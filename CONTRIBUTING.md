# 贡献指南 🤝

感谢您对 GodHand 项目的关注！本指南将帮助您开始贡献。

## 📋 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [测试要求](#测试要求)
- [提交规范](#提交规范)

## 📜 行为准则

- 尊重所有贡献者
- 接受建设性批评
- 关注对社区最有利的事情

## 🚀 如何贡献

### 报告 Bug

1. 检查是否已存在相关问题
2. 使用最新版本验证问题
3. 创建新问题并提供：
   - 清晰的标题和描述
   - 复现步骤
   - 预期行为 vs 实际行为
   - 系统环境信息
   - 相关日志或截图

### 提交功能建议

1. 检查是否已存在相关建议
2. 清晰描述功能及其用例
3. 说明该功能为何对大多数用户有用

### 提交代码

1. Fork 本仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add amazing feature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

## 💻 开发流程

### 环境设置

```bash
# 克隆仓库
git clone https://github.com/Rrocean/godhand.git
cd godhand

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# 安装依赖
make install
```

### 开发工作流

```bash
# 1. 创建分支
git checkout -b feature/your-feature

# 2. 编写代码并测试
make test

# 3. 检查代码风格
make lint

# 4. 提交更改
git add .
git commit -m "feat: add new feature"

# 5. 推送并创建 PR
git push origin feature/your-feature
```

## 📝 代码规范

### Python 代码风格

- 遵循 PEP 8
- 使用 4 空格缩进
- 最大行长度：100 字符
- 使用有意义的变量名

```python
# 好的示例
def detect_ui_elements(screenshot, element_type=None):
    """检测屏幕截图中的 UI 元素。

    Args:
        screenshot: PIL Image 对象
        element_type: 可选的元素类型过滤器

    Returns:
        UIElement 对象列表
    """
    elements = []
    # 实现代码...
    return elements

# 不好的示例
def detect(img, type=None):
    e = []
    # 代码...
    return e
```

### 文档字符串

所有公共函数和类都应包含文档字符串：

```python
class VisualEngine:
    """视觉引擎 - 检测和理解屏幕 UI 元素。

    使用计算机视觉技术检测按钮、输入框等 UI 元素，
    并提供语义理解能力。

    Attributes:
        use_ocr: 是否启用 OCR
        use_ml: 是否使用 ML 模型

    Example:
        >>> engine = VisualEngine(use_ocr=True)
        >>> elements = engine.detect_elements(screenshot)
    """
```

## 🧪 测试要求

### 测试覆盖

- 新功能必须包含单元测试
- 关键路径需要集成测试
- 目标覆盖率：≥ 90%

### 运行测试

```bash
# 所有测试
make test

# 仅单元测试
make test-unit

# 覆盖率报告
make coverage
```

### 测试示例

```python
def test_detect_buttons():
    """测试按钮检测功能"""
    engine = VisualEngine(use_ocr=False)
    screenshot = Image.new('RGB', (800, 600), color='white')

    elements = engine.detect_buttons(screenshot)

    assert isinstance(elements, list)
    assert all(isinstance(e, UIElement) for e in elements)
```

## 🎯 提交规范

使用 [Conventional Commits](https://conventionalcommits.org/)：

- `feat`: 新功能
- `fix`: 修复
- `docs`: 文档
- `style`: 格式（不影响代码含义）
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建/工具

### 示例

```
feat: add voice control support

- Implement VoiceController class
- Add wake word detection
- Integrate with main application

fix: resolve memory leak in VisualEngine

docs: update API documentation for v3.0
test: add unit tests for CloudSync
```

## 🏆 贡献者荣誉

感谢所有贡献者！您可以在 [贡献者页面](https://github.com/Rrocean/godhand/graphs/contributors) 看到所有贡献者。

## ❓ 需要帮助？

- 查看 [文档](docs/)
- 加入 [Discord](https://discord.gg/godhand)（如果有）
- 创建 [Discussion](https://github.com/Rrocean/godhand/discussions)

---

再次感谢您对 GodHand 的贡献！🚀
