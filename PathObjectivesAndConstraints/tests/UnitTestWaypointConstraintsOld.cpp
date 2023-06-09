#include "gtest/gtest.h"
#include "WaypointConstraintsOld.hpp"

TEST(WaypointConstraintOldTests, VelocitiesCase1)
{
    WaypointConstraintsOld<2> waypoint_const{};
    double control_points[] = {3, 0, 9, 5, 7, 8, 0, 1,
                               1, 6, 2, 2, 1, 4, 1, 4};
    bool switches[] = {true, true};
    int num_control_points = 8;
    double scale_factor = 1;
    double true_constraints[] = {-4, -6.5, -0.5, -4};
    double desired_velocities[] = {7, 3, 1, 4};
    double* constraints = waypoint_const.velocity_at_waypoints_constraints(control_points, num_control_points,
                        scale_factor, desired_velocities, switches);
    double tolerance = 0.0000001;
    EXPECT_NEAR(constraints[0], true_constraints[0], tolerance);
    EXPECT_NEAR(constraints[1], true_constraints[1], tolerance);
    EXPECT_NEAR(constraints[2], true_constraints[2], tolerance);
    EXPECT_NEAR(constraints[3], true_constraints[3], tolerance);
}

TEST(WaypointConstraintOldTests, VelocitiesCase2)
{
    WaypointConstraintsOld<3> waypoint_const{};
    double control_points[] = {0, 9, 0, 8, 5, 8, 6, 7,
                               1, 5, 1, 6, 5, 4, 2, 7,
                               5, 4, 5, 6, 8, 7, 5, 9};
    bool switches[] = {true, true};
    int num_control_points = 8;
    double scale_factor = 2;
    double true_constraints[] = {-9, -0.25, -6, -5.25, -8, -7.5};
    double desired_velocities[] = {9, 0, 6, 6, 8, 8};
    double* constraints = waypoint_const.velocity_at_waypoints_constraints(control_points, num_control_points,
                        scale_factor, desired_velocities, switches);
    double tolerance = 0.00001;
    EXPECT_NEAR(constraints[0], true_constraints[0], tolerance);
    EXPECT_NEAR(constraints[1], true_constraints[1], tolerance);
    EXPECT_NEAR(constraints[2], true_constraints[2], tolerance);
    EXPECT_NEAR(constraints[3], true_constraints[3], tolerance);
    EXPECT_NEAR(constraints[4], true_constraints[4], tolerance);
    EXPECT_NEAR(constraints[5], true_constraints[5], tolerance);
}

TEST(WaypointConstraintOldTests, AccelerationCase)
{
    WaypointConstraintsOld<3> waypoint_const{};
    double control_points[] = {0, 9, 0, 8, 5, 8, 6, 7,
                               1, 5, 1, 6, 5, 4, 2, 7,
                               5, 4, 5, 6, 8, 7, 5, 9};
    int num_control_points = 8;
    double scale_factor = 1;
    double true_constraints[] = {-3, -2,
                                 -1,  4,
                                  2,  1};
    double desired_accelerations[] = {-15, 5,
                                       -7, 3,
                                        0, 5};
    bool switches[] = {true, true};
    double* constraints = waypoint_const.acceleration_at_waypoints_constraints(control_points, num_control_points,
                        scale_factor, desired_accelerations,switches);
    double tolerance = 0.00001;
    EXPECT_NEAR(constraints[0], true_constraints[0], tolerance);
    EXPECT_NEAR(constraints[1], true_constraints[1], tolerance);
    EXPECT_NEAR(constraints[2], true_constraints[2], tolerance);
    EXPECT_NEAR(constraints[3], true_constraints[3], tolerance);
    EXPECT_NEAR(constraints[4], true_constraints[4], tolerance);
    EXPECT_NEAR(constraints[5], true_constraints[5], tolerance);
}
