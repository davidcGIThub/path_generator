#ifndef THIRDORDERCURVATUREBOUNDS_HPP
#define THIRDORDERCURVATUREBOUNDS_HPP
#include <array>
#include <eigen3/Eigen/Core>
#include <eigen3/Eigen/Dense>
#include "gtest/gtest_prod.h"
#include "CBindingHelper.hpp"
#include "DerivativeBounds.hpp"
#include "DerivativeEvaluator.hpp"

template <int D> // D is the dimension of the spline
class ThirdOrderCurvatureBounds
{
    public:
        ThirdOrderCurvatureBounds();
        double get_spline_curvature_bound(double cont_pts[], int &num_control_points);
        Eigen::VectorXd get_interval_curvature_bounds(double cont_pts[], int &num_control_points);
        double evaluate_interval_curvature_bound(Eigen::Matrix<double,D,4> &control_points);
    private:
        CBindingHelper<D> cbind_help{};
        DerivativeBounds<D> d_dt_bounds{};
        DerivativeEvaluator<D> d_dt_eval{};
        double find_maximum_cross_term(Eigen::Matrix<double,D,4> &control_points, double &scale_factor);
        Eigen::Vector4d get_2D_cross_coefficients(Eigen::Matrix<double,D,4> &control_points);
        Eigen::Vector4d get_3D_cross_coefficients(Eigen::Matrix<double,D,4> &control_points);
        double calculate_cross_term_magnitude(double &t, Eigen::Matrix<double,D,4> &control_points, double &scale_factor);
    FRIEND_TEST(ThirdOrderCurvatureTest, CrossCoeficients2D);
    FRIEND_TEST(ThirdOrderCurvatureTest, CrossCoeficients3D);
    FRIEND_TEST(ThirdOrderCurvatureTest, CrossTermMagnitude);
    FRIEND_TEST(ThirdOrderCurvatureTest, MaxCrossTerm);
};

#endif

