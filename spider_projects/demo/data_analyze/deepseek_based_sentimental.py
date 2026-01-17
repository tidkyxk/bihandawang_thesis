# config.py - 安全获取API密钥的配置
import os


def get_api_key():
    """
    安全获取API密钥
    查找顺序：
    1. 环境变量 DEEPSEEK_API_KEY
    2. config_secret.py 文件
    3. 用户输入
    """
    # 1. 首先从环境变量获取
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if api_key:
        print("✅ 从环境变量获取API密钥")
        return api_key

    # 2. 从配置文件获取（如果存在）
    try:
        # 注意：config_secret.py 文件不要上传到GitHub
        from spider_projects.demo.demo.spiders.sentiment_orientation.config_secret import DEEPSEEK_API_KEY
        print("✅ 从配置文件获取API密钥")
        return DEEPSEEK_API_KEY
    except ImportError:
        pass  # 继续下一步

    # 3. 如果没有配置文件，提示用户
    print("\n" + "=" * 50)
    print("📝 API密钥配置")
    print("=" * 50)
    print("未找到API密钥配置")
    print("\n请选择配置方式：")
    print("1. 输入API密钥（本次使用）")
    print("2. 创建配置文件（永久保存）")
    print("=" * 50)

    choice = input("\n请选择 (1 或 2): ").strip()

    if choice == "1":
        api_key = input("\n请输入DeepSeek API密钥: ").strip()
        if api_key:
            return api_key

    elif choice == "2":
        api_key = input("\n请输入DeepSeek API密钥: ").strip()
        if api_key:
            try:
                # 创建配置文件
                with open('config_secret.py', 'w', encoding='utf-8') as f:
                    f.write(f'# 这是一个包含API密钥的文件，请不要上传到GitHub！\n')
                    f.write(f'# 可以将此文件添加到 .gitignore 中\n\n')
                    f.write(f'DEEPSEEK_API_KEY = "{api_key}"\n')

                print(f"\n✅ 配置文件已创建: config_secret.py")
                print("⚠️  请确保此文件不被上传到GitHub！")
                print("💡 可以将以下内容添加到 .gitignore 文件：")
                print("   config_secret.py")

                return api_key
            except Exception as e:
                print(f"❌ 创建配置文件失败: {e}")
                return api_key if api_key else None

    return None