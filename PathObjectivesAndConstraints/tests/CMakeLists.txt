set(TEST_NAME ${PROJECT_NAME}_UnitTest)

add_executable(${TEST_NAME}
    UnitTestBsplineToMinvo.cpp
    UnitTestCubicEquationSolver.cpp
    UnitTestMDMAlgorithmClass.cpp
    UnitTestDerivativeEvaluator.cpp
    UnitTestWaypointConstraintsOld.cpp
    UnitTestWaypointConstraints.cpp
    UnitTestObjectiveFunctions.cpp
    UnitTestCurvatureConstraints.cpp
    UnitTestDerivativeBounds.cpp
    UnitTestCrossTermEvaluator.cpp
    UnitTestCrossTermProperties.cpp
    UnitTestCrossTermBounds.cpp
    UnitTestInclineConstraints.cpp
    UnitTestSphereCollisionEvaluator.cpp
    UnitTestObstacleConstraints.cpp)

target_include_directories(${PROJECT_NAME} PUBLIC "${PROJECT_SOURCE_DIR}/src")

target_link_libraries(${TEST_NAME} ${GTEST_LIBRARIES}
    pthread ${GTEST_MAIN_LIBRARIES} ${PROJECT_NAME}
    ${Eigen_LIBRARIES})