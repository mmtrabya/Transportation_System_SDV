#include <unity.h>

void test_math(void) {
    TEST_ASSERT_EQUAL(4, 2 + 2);
}

int main(int argc, char **argv) {
    UNITY_BEGIN();
    RUN_TEST(test_math);
    return UNITY_END();
}
