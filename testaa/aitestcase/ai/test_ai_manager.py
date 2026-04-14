"""
AI管理器测试 - 验证新架构是否正常工作
"""


def test_ai_manager_basic():
    """测试AI管理器基本功能"""
    print("测试AI管理器基本功能...")

    try:
        from .core.manager import AIManager
        from .core.config import AIConfig

        # 创建配置
        config = AIConfig()
        print(f"默认提供商: {config.default_provider}")
        print(f"智谱AI模型: {config.get_model('zhipu')}")
        print(f"DeepSeek模型: {config.get_model('deepseek')}")

        # 创建管理器
        manager = AIManager(provider_name='zhipu', config=config)
        print(f"AI管理器创建成功: {manager.provider_name}")

        # 测试获取统计
        stats = manager.get_statistics()
        print(f"AI统计: {stats}")

        print("[PASS] AI管理器基本功能测试通过")
        return True

    except Exception as e:
        print(f"[FAIL] AI管理器基本功能测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_providers():
    """测试提供商功能"""
    print("\n测试提供商功能...")

    try:
        from .providers import get_available_providers, get_provider_factory

        # 获取可用提供商
        providers = get_available_providers()
        print(f"可用提供商: {providers}")

        # 测试智谱AI提供商工厂
        zhipu_factory = get_provider_factory('zhipu')
        print(f"[PASS] 智谱AI提供商工厂获取成功")

        # 测试DeepSeek提供商工厂
        deepseek_factory = get_provider_factory('deepseek')
        print(f"[PASS] DeepSeek提供商工厂获取成功")

        print("[PASS] 提供商功能测试通过")
        return True

    except Exception as e:
        print(f"[FAIL] 提供商功能测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_prompts():
    """测试提示词功能"""
    print("\n测试提示词功能...")

    try:
        from .prompts.html_parser import HTMLParserPrompt
        from .prompts.test_case import TestCaseGeneratorPrompt
        from .prompts.api_test import APITestCaseGeneratorPrompt

        # 测试HTML解析提示词
        html_content = "<html><body><h1>测试</h1></body></html>"
        html_prompt = HTMLParserPrompt.get_prompt(html_content)
        print(f"[PASS] HTML解析提示词生成成功 (长度: {len(html_prompt)})")

        # 测试测试用例生成提示词
        doc_content = "测试文档内容"
        test_prompt = TestCaseGeneratorPrompt.get_prompt(doc_content)
        print(f"[PASS] 测试用例生成提示词生成成功 (长度: {len(test_prompt)})")

        # 测试API测试用例生成提示词
        api_prompt = APITestCaseGeneratorPrompt.get_prompt(
            api_name="测试接口",
            api_path="/api/test",
            method="POST",
            request_params="参数说明",
            response_params="响应说明",
            remark="备注"
        )
        print(f"[PASS] API测试用例生成提示词生成成功 (长度: {len(api_prompt)})")

        print("[PASS] 提示词功能测试通过")
        return True

    except Exception as e:
        print(f"[FAIL] 提示词功能测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_utils():
    """测试工具功能"""
    print("\n测试工具功能...")

    try:
        from .utils.cache import AICache
        from .utils.monitor import AIMonitor

        # 测试缓存
        cache = AICache(enabled=True, ttl=60)
        print(f"[PASS] 缓存创建成功: {cache.get_stats()}")

        # 测试监控
        monitor = AIMonitor(enabled=True, log_level='INFO')
        stats = monitor.get_statistics()
        print(f"[PASS] 监控创建成功: {stats}")

        print("[PASS] 工具功能测试通过")
        return True

    except Exception as e:
        print(f"[FAIL] 工具功能测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_legacy_compatibility():
    """测试兼容性"""
    print("\n测试兼容性...")

    try:
        from .legacy import (
            get_ai_providers,
            set_api_keys,
            get_api_keys
        )

        # 测试获取提供商
        providers = get_ai_providers()
        print(f"[PASS] 兼容性测试 - 获取提供商: {providers}")

        # 测试设置和获取API密钥
        set_api_keys(zhipu_key="test_zhipu_key")
        keys = get_api_keys()
        print(f"[PASS] 兼容性测试 - API密钥: {keys}")

        print("[PASS] 兼容性测试通过")
        return True

    except Exception as e:
        print(f"[FAIL] 兼容性测试失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("=" * 50)
    print("开始AI抽象层重构测试")
    print("=" * 50)

    results = []

    results.append(("基本功能", test_ai_manager_basic()))
    results.append(("提供商", test_providers()))
    results.append(("提示词", test_prompts()))
    results.append(("工具", test_utils()))
    results.append(("兼容性", test_legacy_compatibility()))

    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)

    for name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{name}: {status}")

    total = len(results)
    passed = sum(1 for _, result in results if result)
    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("[SUCCESS] 所有测试通过！AI抽象层重构成功！")
    else:
        print(f"[WARNING] {total - passed} 个测试失败，请检查错误信息")

    return passed == total


if __name__ == "__main__":
    run_all_tests()
