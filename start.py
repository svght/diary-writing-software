#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动脚本 - 智能新闻工作台
简化依赖检查并启动本地浏览器界面。
"""

import sys
import subprocess


def check_dependencies():
    """检查必要的依赖"""
    required_modules = [
        "flask",
        "requests",
        "geopy",
        "pytz",
    ]

    missing_modules = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing_modules.append(module)
    return missing_modules


def install_dependencies():
    """安装缺失的依赖"""
    print("正在安装必要的依赖...")
    try:
        subprocess.check_call([
            sys.executable, "-m", "pip", "install",
            "Flask", "requests", "geopy", "pytz"
        ])
        print("依赖安装成功！")
        return True
    except subprocess.CalledProcessError as e:
        print(f"安装依赖失败: {e}")
        return False


def main():
    """主函数"""
    print("=" * 50)
    print("智能新闻工作台 - 启动器")
    print("=" * 50)

    missing = check_dependencies()
    if missing:
        print(f"检测到缺失的依赖: {', '.join(missing)}")
        choice = input("是否自动安装依赖？(y/n): ").strip().lower()
        if choice == 'y':
            if not install_dependencies():
                print("依赖安装失败，请手动运行: pip install Flask requests geopy pytz")
                return
        else:
            print("请手动安装依赖: pip install Flask requests geopy pytz")
            return

    try:
        from main import main as start_app
        print("正在启动浏览器界面...")
        print("请稍候，浏览器将自动打开。")
        print("-" * 50)
        start_app()
    except Exception as e:
        print(f"启动应用失败: {e}")
        print("请确保 main.py 和模板文件在当前目录中")


if __name__ == '__main__':
    main()
