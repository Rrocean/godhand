# GodHand Makefile
# 简化开发工作流的常用命令

.PHONY: help install test test-unit test-integration test-e2e benchmark coverage lint format clean run docs

# 默认目标
help:
	@echo "GodHand - 宇宙级 GUI 自动化系统"
	@echo ""
	@echo "可用命令:"
	@echo "  make install        - 安装依赖"
	@echo "  make test           - 运行所有测试"
	@echo "  make test-unit      - 运行单元测试"
	@echo "  make test-integration - 运行集成测试"
	@echo "  make test-e2e       - 运行端到端测试"
	@echo "  make benchmark      - 运行性能基准测试"
	@echo "  make coverage       - 生成测试覆盖率报告"
	@echo "  make lint           - 代码检查"
	@echo "  make format         - 格式化代码"
	@echo "  make clean          - 清理临时文件"
	@echo "  make run            - 启动主程序"
	@echo "  make run-v3         - 启动宇宙版 (v3.0)"
	@echo "  make demo           - 运行宇宙级演示"
	@echo "  make docs           - 生成文档"

# 安装依赖
install:
	pip install -r requirements.txt
	pip install pytest pytest-cov flake8 black

# 运行所有测试
test:
	python tests/run_all_tests.py

# 单元测试
test-unit:
	python -m pytest tests/test_*.py -v -m "not integration and not e2e and not benchmark"

# 集成测试
test-integration:
	python tests/test_integration.py

# 端到端测试
test-e2e:
	python tests/test_end_to_end.py

# 性能基准测试
benchmark:
	python tests/benchmark_performance.py

# 测试覆盖率
coverage:
	python -m pytest tests/ --cov=core --cov-report=html --cov-report=term
	@echo "覆盖率报告: htmlcov/index.html"

# 代码检查
lint:
	flake8 core/ --count --select=E9,F63,F7,F82 --show-source --statistics
	flake8 core/ --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics

# 格式化代码
format:
	black core/ tests/ examples/ --line-length 100

# 清理临时文件
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage 2>/dev/null || true
	rm -rf build/ dist/ 2>/dev/null || true

# 启动程序
run:
	python main.py

# 启动宇宙版
run-v3:
	python main_v3.py

# 运行演示
demo:
	python examples/universe_demo.py

# 生成文档
docs:
	@echo "文档位于 docs/ 目录"
	@echo "主要文档:"
	@echo "  - docs/UNIVERSE_FIRST_ACHIEVED.md"
	@echo "  - docs/WORLD_NUMBER_ONE_CHECKLIST.md"
	@echo "  - docs/ROADMAP_TO_WORLD_NUMBER_ONE.md"

# 快速检查（用于CI）
ci-check: lint test-unit
	@echo "CI 检查完成"
