# mini_unittest.py

import time
import traceback
from typing import Dict, List, Callable, Any, Optional, Type
from functools import wraps


class TestCase:
    """测试用例基类 - 提供测试的基本结构和方法"""

    def __init__(self, name: str = ""):
        self.name = name or self.__class__.__name__
        self.test_methods = []

    def setUp(self):
        """测试前准备方法，子类可重写"""
        pass

    def tearDown(self):
        """测试后清理方法，子类可重写"""
        pass

    def run(self) -> 'TestResult':
        """执行测试用例中的所有测试方法"""
        result = TestResult(self)

        # 获取所有测试方法
        test_methods = [getattr(self, method) for method in dir(self)
                        if method.startswith('test_') and callable(getattr(self, method))]

        for test_method in test_methods:
            try:
                # 执行setUp
                self.setUp()

                # 执行测试方法
                start_time = time.time()
                test_method()
                end_time = time.time()

                # 记录成功
                result.add_success(test_method.__name__, end_time - start_time)

                # 执行tearDown
                self.tearDown()

            except AssertionError as e:
                result.add_failure(test_method.__name__, str(e))
                self.tearDown()

            except Exception as e:
                result.add_error(test_method.__name__, traceback.format_exc())
                self.tearDown()

        return result

    def assertEqual(self, first: Any, second: Any, msg: str = ""):
        """断言两个值相等"""
        if first != second:
            raise AssertionError(f"{first} != {second} {msg}")

    def assertNotEqual(self, first: Any, second: Any, msg: str = ""):
        """断言两个值不相等"""
        if first == second:
            raise AssertionError(f"{first} == {second} {msg}")

    def assertTrue(self, expr: bool, msg: str = ""):
        """断言表达式为True"""
        if not expr:
            raise AssertionError(f"Expression is not true {msg}")

    def assertFalse(self, expr: bool, msg: str = ""):
        """断言表达式为False"""
        if expr:
            raise AssertionError(f"Expression is not false {msg}")

    def assertIn(self, item: Any, container: Any, msg: str = ""):
        """断言item在container中"""
        if item not in container:
            raise AssertionError(f"{item} not in {container} {msg}")

    def assertIsNone(self, obj: Any, msg: str = ""):
        """断言对象为None"""
        if obj is not None:
            raise AssertionError(f"{obj} is not None {msg}")


# screenshot_utils.py
import os
from selenium import webdriver
from datetime import datetime
import logging


class ScreenshotManager:
    def __init__(self, screenshot_dir='screenshots'):
        self.screenshot_dir = screenshot_dir
        if not os.path.exists(screenshot_dir):
            os.makedirs(screenshot_dir)

    def take_screenshot(self, driver, test_name, status):
        """
        截图功能
        :param driver: WebDriver实例
        :param test_name: 测试名称
        :param status: 测试状态 (success/failure)
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]
            filename = f"{test_name}_{status}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)

            # 截图
            driver.save_screenshot(filepath)
            logging.info(f"Screenshot saved: {filepath}")

            return filepath
        except Exception as e:
            logging.error(f"Failed to take screenshot: {str(e)}")
            return None

class TestResult:
    """测试结果记录器 - 记录和管理测试执行结果"""

    def __init__(self, test_case: TestCase):
        self.test_case = test_case
        self.successes: List[Dict] = []  # 成功测试列表
        self.failures: List[Dict] = []  # 失败测试列表
        self.errors: List[Dict] = []  # 错误测试列表

    def starttest(self, test_name: str, test_id: float):
        super().starttest(test_id)
        self.test_logs[test_id] = {
            'start_time': datetime.now(),
            'log_buffer': []
        }

        # 清空日志捕获器
        self.log_capture.truncate(0)
        self.log_capture.seek(0)

        print(f"\n开始执行测试: {test_name}")

    def stopTest(self, test):
        """测试结束时调用"""
        super().stopTest(test)

        # 获取测试结束时间
        end_time = datetime.now()
        test_info = self.test_logs.get(test, {})
        start_time = test_info.get('start_time', end_time)
        duration = (end_time - start_time).total_seconds()

        # 获取捕获的日志
        execution_log = self.log_capture.getvalue()

        # 准备日志数据
        log_data = {
            'test_name': test._testMethodName,
            'test_module': test.__class__.__name__,
            'start_time': start_time,
            'end_time': end_time,
            'duration': duration,
            'execution_log': execution_log,
            'additional_data': {
                'description': test.shortDescription()
            }
        }

        # 根据测试结果设置状态和截图
        if test in self.failures:
            log_data['status'] = 'FAILED'
            log_data['error_message'] = str(self.failures[test][0])
            log_data['traceback'] = self.failures[test][1]
            self._take_screenshot(test, 'failure')

        elif test in self.errors:
            log_data['status'] = 'ERROR'
            log_data['error_message'] = str(self.errors[test][0])
            log_data['traceback'] = self.errors[test][1]
            self._take_screenshot(test, 'error')

        else:
            log_data['status'] = 'SUCCESS'
            self._take_screenshot(test, 'success')

        # 保存到数据库
        log_id = self.db.insert_log(log_data)
        print(f"测试日志已保存，ID: {log_id}")

        # 清理
        self.test_logs.pop(test, None)

    def add_success(self, test_name: str, duration: float):
        """记录成功的测试"""

        self.successes.append({
            'name': test_name,
            'duration': duration
        })

    def add_failure(self, test_name: str, message: str):
        """记录失败的测试（断言失败）"""
        self.failures.append({
            'name': test_name,
            'message': message
        })

    def add_error(self, test_name: str, traceback: str):
        """记录错误的测试（代码异常）"""
        self.errors.append({
            'name': test_name,
            'traceback': traceback
        })

    def was_successful(self) -> bool:
        """判断测试是否全部成功"""
        return len(self.failures) == 0 and len(self.errors) == 0

    def __str__(self):
        """格式化输出测试结果"""
        total = len(self.successes) + len(self.failures) + len(self.errors)
        output = [
            f"\n{'=' * 60}",
            f"Test Case: {self.test_case.name}",
            f"{'=' * 60}",
            f"Total tests: {total}",
            f"Success: {len(self.successes)}",
            f"Failures: {len(self.failures)}",
            f"Errors: {len(self.errors)}",
        ]

        if self.failures:
            output.append(f"\n{'=' * 60}")
            output.append("FAILURES:")
            for f in self.failures:
                output.append(f"  ✗ {f['name']}: {f['message']}")

        if self.errors:
            output.append(f"\n{'=' * 60}")
            output.append("ERRORS:")
            for e in self.errors:
                output.append(f"  ✗ {e['name']}:")
                output.append(f"{e['traceback']}")

        return "\n".join(output)

    def _take_screenshot(self, test, status):
        """
        截图方法，需要在具体的测试类中实现
        """
        try:
            # 尝试从测试实例中获取driver
            if hasattr(test, 'driver'):
                screenshot_path = self.screenshot_manager.take_screenshot(
                    test.driver,
                    test._testMethodName,
                    status
                )
                if screenshot_path:
                    # 更新日志数据中的截图路径
                    test_info = self.test_logs.get(test, {})
                    test_info['screenshot_path'] = screenshot_path
                    print(f"截图已保存: {screenshot_path}")
            else:
                print("未找到WebDriver实例，无法截图")
        except Exception as e:
            print(f"截图失败: {str(e)}")


class TestSuite:
    """测试套件 - 管理和组织多个测试用例"""

    def __init__(self):
        self.test_cases: List[TestCase] = []

    def add_test(self, test_case: TestCase):
        """添加测试用例"""
        self.test_cases.append(test_case)

    def add_tests(self, *test_cases: TestCase):
        """添加多个测试用例"""
        self.test_cases.extend(test_cases)

    def run(self) -> List[TestResult]:
        """运行所有测试用例"""
        results = []
        print(f"\nRunning Test Suite with {len(self.test_cases)} test cases")

        for test_case in self.test_cases:
            result = test_case.run()
            results.append(result)
            print(str(result))

        return results


class TestLoader:
    """测试加载器 - 发现和加载测试用例"""

    @staticmethod
    def load_from_module(module) -> TestSuite:
        """从模块加载测试用例"""
        suite = TestSuite()

        for name in dir(module):
            obj = getattr(module, name)
            # 检查是否为TestCase的子类且不是TestCase本身
            if (isinstance(obj, type) and
                    issubclass(obj, TestCase) and
                    obj != TestCase):
                suite.add_test(obj())

        return suite

    @staticmethod
    def load_from_class(test_class: Type[TestCase]) -> TestCase:
        """从测试类加载测试用例"""
        return test_class()

    @staticmethod
    def discover(pattern: str = "test_*.py") -> TestSuite:
        """发现测试文件（简化版）"""
        # 在实际项目中，这里应该扫描目录
        # 这里简化实现
        suite = TestSuite()
        return suite


class TestRunner:
    """测试运行器 - 控制测试执行流程"""

    def __init__(self, verbosity: int = 1):
        self.verbosity = verbosity
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None

    def run(self, test_suite: TestSuite) -> Dict:
        """运行测试套件"""
        self.start_time = time.time()

        print(f"\n{'=' * 60}")
        print("Test Runner Started")
        print(f"{'=' * 60}")

        # 运行测试套件
        results = test_suite.run()

        self.end_time = time.time()
        duration = self.end_time - self.start_time

        # 汇总统计
        total_tests = sum(len(r.successes) + len(r.failures) + len(r.errors)
                          for r in results)
        total_failures = sum(len(r.failures) for r in results)
        total_errors = sum(len(r.errors) for r in results)

        # 输出总结
        print(f"\n{'=' * 60}")
        print("Test Summary")
        print(f"{'=' * 60}")
        print(f"Total test cases: {len(results)}")
        print(f"Total tests: {total_tests}")
        print(f"Failures: {total_failures}")
        print(f"Errors: {total_errors}")
        print(f"Duration: {duration:.3f}s")

        if total_failures == 0 and total_errors == 0:
            print("\n✅ ALL TESTS PASSED")
        else:
            print("\n❌ SOME TESTS FAILED")

        return {
            'total_cases': len(results),
            'total_tests': total_tests,
            'failures': total_failures,
            'errors': total_errors,
            'duration': duration,
            'results': results
        }


# 装饰器 - 提供额外的测试功能
def skip(reason: str = ""):
    """跳过测试的装饰器"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            raise unittest.SkipTest(reason)

        return wrapper

    return decorator


def expected_failure(func):
    """标记测试为预期失败的装饰器"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except AssertionError:
            pass  # 预期失败
        else:
            raise AssertionError(f"{func.__name__} unexpectedly passed")

    return wrapper