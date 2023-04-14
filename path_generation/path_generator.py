"""
This module generates a 3rd order B-spline path between two waypoints,
waypoint directions, curvature constraint, and adjoining 
safe flight corridors.
"""
import os
import numpy as np
from scipy.optimize import minimize, Bounds, LinearConstraint, NonlinearConstraint, Bounds
from path_generation.matrix_evaluation import get_M_matrix
from PathObjectivesAndConstraints.python_wrappers.objective_functions import ObjectiveFunctions
from PathObjectivesAndConstraints.python_wrappers.curvature_constraints import CurvatureConstraints
from PathObjectivesAndConstraints.python_wrappers.obstacle_constraints import ObstacleConstraints
from PathObjectivesAndConstraints.python_wrappers.incline_constraints import InclineConstraints
from PathObjectivesAndConstraints.python_wrappers.waypoint_constraints import WaypointConstraints
from bsplinegenerator.bspline_to_minvo import get_composite_bspline_to_minvo_conversion_matrix
from path_generation.obstacle import Obstacle
import time



class PathGenerator:
    """
    This class generates a 3rd order B-spline path between two waypoints,
    waypoint directions, curvature constraint, and adjoining 
    safe flight corridors.
    """

# when minimizing distance and time need constraint over max velocity
# when minimizing acceleration, no max velocity constraint needed

    def __init__(self, dimension: int):
        self._dimension = dimension
        self._order = 3
        self._M = get_M_matrix(self._order)
        self._control_points_per_corridor = 4
        self._objective_func_obj = ObjectiveFunctions(self._dimension)
        self._curvature_const_obj = CurvatureConstraints(self._dimension)
        self._waypoint_const_obj = WaypointConstraints(self._dimension)
        self._obstacle_cons_obj = ObstacleConstraints(self._dimension)
        if dimension == 3:
            self._incline_const_obj = InclineConstraints()
        
    def generate_path(self, point_sequence: np.ndarray, waypoint_directions: np.ndarray = None, 
                waypoint_accelerations: np.ndarray = None, max_curvature: np.float64 = None,
                max_incline = None, sfcs: list = None, obstacles = None):
        num_sfcs = self.__get_num_sfcs(sfcs)
        intervals_per_corridor = self.get_intervals_per_corridor(num_sfcs,point_sequence)
        num_intervals = np.sum(intervals_per_corridor)
        num_cont_pts = self.__get_num_control_points(num_intervals)
        constraints = self.__get_constraints(num_cont_pts, intervals_per_corridor, point_sequence, 
                waypoint_directions, waypoint_accelerations, max_curvature, max_incline, sfcs, obstacles)
        initial_control_points = self.__create_initial_control_points(point_sequence, num_cont_pts)
        initial_scale_factor = 1
        optimization_variables = np.concatenate((initial_control_points.flatten(),[initial_scale_factor]))
        objectiveFunction = self.__get_objective_function()
        objective_variable_bounds = self.__create_objective_variable_bounds(num_cont_pts)
        minimize_options = {'disp': False} #, 'maxiter': self.maxiter, 'ftol': tol}
        # perform optimization
        start_time = time.time()
        result = minimize(
            objectiveFunction,
            x0=optimization_variables,
            args=(num_cont_pts,),
            method='SLSQP', 
            bounds=objective_variable_bounds,
            constraints=constraints, 
            options = minimize_options)
        optimized_control_points = np.reshape(result.x[0:-1] ,(self._dimension,num_cont_pts))
        return optimized_control_points
        
    def __get_constraints(self, num_cont_pts: int, intervals_per_corridor: tuple, point_sequence: np.ndarray, 
            waypoint_directions: np.ndarray, waypoint_accelerations: np.ndarray, max_curvature: np.float64,  
            max_incline: np.float64, sfcs: list, obstacles: list):
        waypoints = np.concatenate((point_sequence[:,0][:,None], point_sequence[:,-1][:,None]),1)
        waypoint_constraint = self.__create_waypoint_constraint(waypoints, num_cont_pts)
        constraints = [waypoint_constraint]
        if waypoint_directions is not None:
            vel_mags = np.linalg.norm(waypoint_directions,2,0)
            if np.sum(vel_mags) > 0.000000001:
                switches = np.array([True, True])
                normalized_directions = waypoint_directions/vel_mags
                if vel_mags[0] < 0.0000000001:
                    switches[0] = False
                if vel_mags[1] < 0.0000000001:
                    switches[1] = False
                direction_constraint = self.__create_waypoint_direction_constraint(normalized_directions, num_cont_pts, switches)
                constraints.append(direction_constraint)
        if waypoint_accelerations is not None:
            accel_mags = np.linalg.norm(waypoint_accelerations,2,0)
            if np.sum(accel_mags) > 0.000000001:
                switches = np.array([True, True])
                if accel_mags[0] < 0.0000000001:
                    switches[0] = False
                if accel_mags[1] < 0.0000000001:
                    switches[1] = False
                waypoint_accel_constraint = self.__create_waypoint_acceleration_constraint(waypoint_accelerations, num_cont_pts, switches)
                constraints.append(waypoint_accel_constraint)
        if max_curvature is not None:
            curvature_constraint = self.__create_curvature_constraint(max_curvature, num_cont_pts)
            constraints.append(curvature_constraint)
        if max_incline is not None:
            incline_constraint = self.__create_incline_constraints(max_incline, num_cont_pts)
            constraints.append(incline_constraint)
        num_sfcs = self.__get_num_sfcs(sfcs)
        if num_sfcs > 0:
            sfc_constraint = self.__create_safe_flight_corridor_constraint(sfcs, num_cont_pts, intervals_per_corridor)
            constraints.append(sfc_constraint)
        if (obstacles != None):
            obstacle_constraint = self.__create_obstacle_constraints(obstacles, num_cont_pts)
            constraints.append(obstacle_constraint)
        return tuple(constraints)

# bounds over just the scale factor
    def __create_objective_variable_bounds(self, num_cont_pts):
        lower_bounds = np.zeros(num_cont_pts*self._dimension + 1) - np.inf
        upper_bounds = np.zeros(num_cont_pts*self._dimension + 1) + np.inf
        lower_bounds[num_cont_pts*self._dimension] = 0.00001
        return Bounds(lb=lower_bounds, ub = upper_bounds)
    
    def __get_objective_function(self):
        # return self.__minimize_distance_objective_function
        return self.__minimize_acceleration_objective_function

    def __minimize_acceleration_objective_function(self, variables, num_cont_pts):
        # for third order splines only
        control_points = np.reshape(variables[0:num_cont_pts*self._dimension], \
            (self._dimension,num_cont_pts))
        scale_factor = variables[-1]
        return self._objective_func_obj.minimize_acceleration_and_time(control_points, scale_factor)

    def __create_waypoint_constraint(self, waypoints, num_cont_pts):
        num_waypoints = 2
        m = num_waypoints
        n = num_cont_pts
        k = self._order
        d = self._dimension
        constraint_matrix = np.zeros((m*d,n*d))
        Gamma_0 = np.zeros((self._order+1,1))
        Gamma_0[self._order,0] = 1
        Gamma_f = np.ones((self._order+1,1))
        M_Gamma_0_T = np.dot(self._M,Gamma_0).T
        M_Gamma_f_T = np.dot(self._M,Gamma_f).T
        for i in range(self._dimension):
            constraint_matrix[i*m   ,  i*n        : i*n+k+1] = M_Gamma_0_T
            constraint_matrix[i*m+1 , (i+1)*n-k-1 : (i+1)*n] = M_Gamma_f_T
        constraint_matrix = np.concatenate((constraint_matrix,np.zeros((m*d,1))),1)
        constraint = LinearConstraint(constraint_matrix, lb=waypoints.flatten(), ub=waypoints.flatten())
        return constraint

    def __create_waypoint_direction_constraint(self, normalized_directions, num_cont_pts, switches):
        lower_bound = 0
        upper_bound = 0
        def velocity_constraint_function(variables):
            control_points = np.reshape(variables[0:num_cont_pts*self._dimension], \
            (self._dimension,num_cont_pts))
            scale_factor = variables[-1]
            constraints = self._waypoint_const_obj.velocity_at_waypoints_constraints(control_points,
                scale_factor, normalized_directions, switches)
            if switches[0] == False:
                return np.reshape(constraints,(self._dimension,2))[:,1].flatten()
            if switches[1] == False:
                return np.reshape(constraints,(self._dimension,2))[:,0].flatten()
            return constraints.flatten()
        velocity_vector_constraint = NonlinearConstraint(velocity_constraint_function, lb= lower_bound, ub=upper_bound)
        return velocity_vector_constraint
    
    def __create_waypoint_acceleration_constraint(self, waypoint_accelerations, num_cont_pts, switches):
        lower_bound = 0
        upper_bound = 0
        def acceleration_constraint_function(variables):
            control_points = np.reshape(variables[0:num_cont_pts*self._dimension], \
            (self._dimension,num_cont_pts))
            scale_factor = variables[-1]
            # constraints = self._waypoint_const_obj.acceleration_at_waypoints_constraints(control_points,
            #     scale_factor, waypoint_accelerations)
            constraints = (control_points[:,0] - 2*control_points[:,1] + control_points[:,2]) - waypoint_accelerations[:,0]
            # if switches[0] == False:
            #     return np.reshape(constraints,(self._dimension,2))[:,1].flatten()
            # if switches[1] == False:
            #     return np.reshape(constraints,(self._dimension,2))[:,0].flatten()
            return constraints.flatten()
        acceleration_vector_constraint = NonlinearConstraint(acceleration_constraint_function, lb= lower_bound, ub=upper_bound)
        return acceleration_vector_constraint

    def __create_curvature_constraint(self, max_curvature, num_cont_pts):
        num_intervals = num_cont_pts - self._order
        def curvature_constraint_function(variables):
            control_points = np.reshape(variables[0:num_cont_pts*self._dimension], \
            (self._dimension,num_cont_pts))
            # return self._curvature_const_obj.get_interval_curvature_constraints(control_points,max_curvature)
            return self._curvature_const_obj.get_spline_curvature_constraint(control_points,max_curvature)
        lower_bound = - np.inf
        upper_bound = 0
        curvature_constraint = NonlinearConstraint(curvature_constraint_function , lb = lower_bound, ub = upper_bound)
        return curvature_constraint
    
    def __create_incline_constraints(self, max_incline, num_cont_pts):
        def incline_constraint_function(variables):
            control_points = np.reshape(variables[0:num_cont_pts*self._dimension], \
            (self._dimension,num_cont_pts))
            scale_factor = variables[-1]
            constraint = self._incline_const_obj.get_spline_incline_constraint(control_points, scale_factor, max_incline)
            return constraint
        lower_bound = - np.inf
        upper_bound = 0
        incline_constraint = NonlinearConstraint(incline_constraint_function , lb = lower_bound, ub = upper_bound)
        return incline_constraint

    def __create_safe_flight_corridor_constraint(self, sfcs, num_cont_pts, intervals_per_corridor):
        # create the rotation matrix.
        num_corridors = self.__get_num_sfcs(sfcs)
        num_minvo_cont_pts = (num_cont_pts - self._order)*(self._order+1)
        M_rot = self.get_composite_sfc_rotation_matrix(intervals_per_corridor, sfcs, num_minvo_cont_pts)
        # create the bspline to minvo conversion matrix 
        M_minvo = get_composite_bspline_to_minvo_conversion_matrix(\
            num_cont_pts, self._order)
        zero_block = np.zeros((num_minvo_cont_pts,num_cont_pts))
        zero_col = np.zeros((num_minvo_cont_pts, 1))
        if self._dimension == 2:
            M_minvo = np.block([[M_minvo, zero_block, zero_col],
                                        [zero_block, M_minvo, zero_col]])
        if self._dimension == 3:
            M_minvo = np.block([[M_minvo,    zero_block, zero_block, zero_col],
                                [zero_block, M_minvo   , zero_block, zero_col],
                                [zero_block, zero_block, M_minvo   , zero_col]])
        conversion_matrix = M_rot @ M_minvo
        #create bounds
        lower_bounds = np.zeros((self._dimension, num_minvo_cont_pts))
        upper_bounds = np.zeros((self._dimension, num_minvo_cont_pts))
        index = 0
        for corridor_index in range(num_corridors):
            num_intervals = intervals_per_corridor[corridor_index]
            lower_bound, upper_bound = sfcs[corridor_index].getRotatedBounds()
            num_points = num_intervals*(self._order+1)
            lower_bounds[:,index:index+num_points] = lower_bound
            upper_bounds[:,index:index+num_points] = upper_bound
            index = index+num_points
        safe_corridor_constraints = LinearConstraint(conversion_matrix, lb=lower_bounds.flatten(), ub=upper_bounds.flatten())
        return safe_corridor_constraints
    
    def __create_obstacle_constraints(self, obstacles, num_cont_pts):
        num_intervals = num_cont_pts - self._order
        def obstacle_constraint_function(variables):
            control_points = np.reshape(variables[0:num_cont_pts*self._dimension], \
            (self._dimension,num_cont_pts))
            # return self._obstacle_cons_obj.getObstacleConstraintsForIntervals(control_points, obstacle.radius, obstacle.center)
            radii = np.zeros(len(obstacles))
            centers = np.zeros((self._dimension,len(obstacles)))
            for i in range(len(obstacles)):
                radii[i] = obstacles[i].radius
                centers[0,i] = obstacles[i].center[0,0]
                centers[1,i] = obstacles[i].center[1,0]
                if self._dimension == 3:
                    centers[2,i] = obstacles[i].center[2,0]
            return self._obstacle_cons_obj.getObstaclesConstraintsForSpline(control_points, radii, centers)
        lower_bound = 0
        upper_bound = np.inf
        obstacle_constraint = NonlinearConstraint(obstacle_constraint_function , lb = lower_bound, ub = upper_bound)
        return obstacle_constraint
    
    def get_composite_sfc_rotation_matrix(self, intervals_per_corridor, sfcs, num_minvo_cont_pts):
        num_corridors = len(intervals_per_corridor)
        M_len = num_minvo_cont_pts*self._dimension
        M_rot = np.zeros((M_len, M_len))
        num_cont_pts_per_interval = self._order + 1
        interval_count = 0
        dim_step = num_minvo_cont_pts
        for corridor_index in range(num_corridors):
            rotation = sfcs[corridor_index].rotation.T
            num_intervals = intervals_per_corridor[corridor_index]
            for interval_index in range(num_intervals):
                for cont_pt_index in range(num_cont_pts_per_interval):
                    index = interval_count*num_cont_pts_per_interval+cont_pt_index
                    M_rot[index, index] = rotation[0,0]
                    M_rot[index, index + dim_step] = rotation[0,1]
                    M_rot[index + dim_step, index] = rotation[1,0]
                    M_rot[index + dim_step, index + dim_step] = rotation[1,1]
                    if self._dimension == 3:
                        M_rot[2*dim_step + index, index] = rotation[2,0]
                        M_rot[2*dim_step + index, index + dim_step] = rotation[2,1]
                        M_rot[2*dim_step + index, index + 2*dim_step] = rotation[2,2]
                        M_rot[dim_step + index, index + 2*dim_step] = rotation[1,2]
                        M_rot[index, index + 2*dim_step] = rotation[0,2]
                interval_count += 1
        return M_rot

    def get_intervals_per_corridor(self, total_num_corridors, point_sequence):
        if total_num_corridors < 2:
            intervals_per_corridor = 5
        else:
            distances = np.linalg.norm(point_sequence[:,1:] - point_sequence[:,0:-1],2,0)
            min_distance = np.min(distances)
            intervals_per_corridor = []
            for i in range(total_num_corridors):
                num_intervals = int(np.round(distances[i]/min_distance)) + 1
                intervals_per_corridor.append(num_intervals)
        return intervals_per_corridor

    def __create_initial_control_points(self, point_sequence, total_num_cont_pts):
        num_segments = np.shape(point_sequence)[1] - 1
        if num_segments < 2:
            start_point = point_sequence[:,0]
            end_point = point_sequence[:,1]
            control_points = np.linspace(start_point,end_point,total_num_cont_pts).T
        else:
            control_points = np.empty(shape=(self._dimension,0))
            distances = np.linalg.norm(point_sequence[:,1:] - point_sequence[:,0:-1],2,0)
            total_distance = np.sum(distances)
            distance_between_cps = total_distance/(total_num_cont_pts-1)
            remainder_distance = 0
            for i in range(len(distances)):
                distance = distances[i] - remainder_distance
                num_cont_pts = int(np.ceil(distance / distance_between_cps))
                # if i == len(distances) - 1:
                #     num_cont_pts -= 2
                remainder_distance = distance % distance_between_cps
                segment_control_points = np.linspace(point_sequence[:,i],point_sequence[:,i+1],
                                                     num_cont_pts).T
                control_points = np.concatenate((control_points, segment_control_points),1)
        return control_points
        
    def __get_num_control_points(self, num_intervals):
        num_control_points = num_intervals + self._order
        return int(num_control_points)
    
    def __get_num_sfcs(self, sfcs):
        if sfcs == None:
            return int(0)
        else:
            return int(len(sfcs))
        