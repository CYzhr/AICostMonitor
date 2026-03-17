#!/bin/bash
# 简易 Skill Vetter - 技能质量审查工具
# 提供基本的技能质量评估功能

set -e

echo "🔍 Skill Vetter - 技能质量审查工具"
echo "======================================"

if [ -z "$1" ]; then
    echo "使用方法: ./skill-vetter-basic.sh <技能目录路径>"
    echo "示例: ./skill-vetter-basic.sh /root/.openclaw/workspace/skills/find-skills"
    exit 1
fi

SKILL_DIR="$1"
if [ ! -d "$SKILL_DIR" ]; then
    echo "❌ 错误: 技能目录不存在: $SKILL_DIR"
    exit 1
fi

echo "正在审查技能: $(basename "$SKILL_DIR")"
echo "技能路径: $SKILL_DIR"
echo "--------------------------------------"

# 1. 检查核心文件
echo "📋 1. 核心文件检查:"
REQUIRED_FILES=("SKILL.md" "README.md" "package.json")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$SKILL_DIR/$file" ]; then
        echo "  ✅ $file - 存在"
    else
        echo "  ⚠️  $file - 缺失"
    fi
done

# 2. 文档质量检查
echo ""
echo "📚 2. 文档质量检查:"
if [ -f "$SKILL_DIR/SKILL.md" ]; then
    LINES=$(wc -l < "$SKILL_DIR/SKILL.md")
    echo "  SKILL.md 行数: $LINES 行"
    
    # 检查关键部分
    if grep -q "## When to Use This Skill" "$SKILL_DIR/SKILL.md"; then
        echo "  ✅ 包含 'When to Use This Skill' 部分"
    else
        echo "  ⚠️  缺失 'When to Use This Skill' 部分"
    fi
    
    if grep -q "## How to Use" "$SKILL_DIR/SKILL.md"; then
        echo "  ✅ 包含 'How to Use' 部分"
    else
        echo "  ⚠️  缺失 'How to Use' 部分"
    fi
fi

# 3. 代码结构检查
echo ""
echo "💻 3. 代码结构检查:"
TOTAL_FILES=$(find "$SKILL_DIR" -type f -name "*.js" -o -name "*.ts" -o -name "*.py" -o -name "*.sh" | wc -l)
echo "  代码文件总数: $TOTAL_FILES"

# 查找主执行文件
MAIN_FILES=$(find "$SKILL_DIR" -type f \( -name "index.*" -o -name "main.*" -o -name "skill.*" \) | head -5)
if [ -n "$MAIN_FILES" ]; then
    echo "  ✅ 找到主执行文件:"
    echo "$MAIN_FILES" | sed 's/^/    /'
else
    echo "  ⚠️  未找到明确的主执行文件"
fi

# 4. 依赖检查
echo ""
echo "📦 4. 依赖检查:"
if [ -f "$SKILL_DIR/package.json" ]; then
    DEPS=$(grep -c '"dependencies"' "$SKILL_DIR/package.json" || echo 0)
    DEV_DEPS=$(grep -c '"devDependencies"' "$SKILL_DIR/package.json" || echo 0)
    echo "  生产依赖: $DEPS 个"
    echo "  开发依赖: $DEV_DEPS 个"
fi

# 5. 安全性检查
echo ""
echo "🔒 5. 基本安全检查:"
# 检查常见敏感模式
SENSITIVE_PATTERNS=("API_KEY" "SECRET" "PASSWORD" "TOKEN" "PRIVATE")
PATTERN_COUNT=0
for pattern in "${SENSITIVE_PATTERNS[@]}"; do
    if grep -r -i "$pattern" "$SKILL_DIR" --include="*.js" --include="*.ts" --include="*.py" --include="*.json" 2>/dev/null | grep -v "node_modules" | head -1 > /dev/null; then
        PATTERN_COUNT=$((PATTERN_COUNT + 1))
    fi
done

if [ $PATTERN_COUNT -gt 0 ]; then
    echo "  ⚠️  发现 $PATTERN_COUNT 个可能的敏感模式"
    echo "    建议: 检查技能是否妥善处理敏感信息"
else
    echo "  ✅ 未发现明显的敏感模式"
fi

# 6. 许可证检查
echo ""
echo "⚖️ 6. 许可证检查:"
LICENSE_FILES=$(find "$SKILL_DIR" -type f -iname "license*" -o -iname "licence*" | head -3)
if [ -n "$LICENSE_FILES" ]; then
    echo "  ✅ 找到许可证文件:"
    echo "$LICENSE_FILES" | sed 's/^/    /'
    
    # 显示许可证类型
    FIRST_LICENSE=$(echo "$LICENSE_FILES" | head -1)
    if [ -f "$FIRST_LICENSE" ]; then
        LICENSE_TYPE=$(head -5 "$FIRST_LICENSE" | grep -i "MIT\|Apache\|GPL\|BSD" || echo "未知")
        echo "  许可证类型: $LICENSE_TYPE"
    fi
else
    echo "  ⚠️  未找到许可证文件"
fi

# 7. 总结评分
echo ""
echo "📊 7. 技能质量总结:"

SCORE=0
TOTAL_POINTS=7

# 计分逻辑
[ -f "$SKILL_DIR/SKILL.md" ] && SCORE=$((SCORE + 1))
[ -f "$SKILL_DIR/README.md" ] && SCORE=$((SCORE + 1))
[ -f "$SKILL_DIR/package.json" ] && SCORE=$((SCORE + 1))
[ "$TOTAL_FILES" -gt 0 ] && SCORE=$((SCORE + 1))
[ -n "$MAIN_FILES" ] && SCORE=$((SCORE + 1))
[ "$PATTERN_COUNT" -eq 0 ] && SCORE=$((SCORE + 1))
[ -n "$LICENSE_FILES" ] && SCORE=$((SCORE + 1))

PERCENTAGE=$((SCORE * 100 / TOTAL_POINTS))

echo "  质量评分: $SCORE/$TOTAL_POINTS ($PERCENTAGE%)"

if [ $PERCENTAGE -ge 85 ]; then
    echo "  🏆 评级: 优秀"
elif [ $PERCENTAGE -ge 70 ]; then
    echo "  👍 评级: 良好"
elif [ $PERCENTAGE -ge 50 ]; then
    echo "  ⚠️  评级: 一般"
else
    echo "  ❌ 评级: 需要改进"
fi

echo ""
echo "======================================"
echo "🔧 建议改进项:"
[ ! -f "$SKILL_DIR/SKILL.md" ] && echo "  - 添加 SKILL.md 文件（技能说明文档）"
[ ! -f "$SKILL_DIR/README.md" ] && echo "  - 添加 README.md 文件（用户文档）"
[ ! -f "$SKILL_DIR/package.json" ] && echo "  - 添加 package.json（依赖管理）"
[ "$TOTAL_FILES" -eq 0 ] && echo "  - 添加实现代码文件"
[ -z "$MAIN_FILES" ] && echo "  - 明确主执行文件（index.js/main.js等）"
[ $PATTERN_COUNT -gt 0 ] && echo "  - 检查并妥善处理敏感信息"
[ -z "$LICENSE_FILES" ] && echo "  - 添加开源许可证文件"

echo ""
echo "✅ 审查完成！"
echo "💡 提示: 完整的 Skill Vetter 工具提供更详细的安全扫描、性能测试和依赖分析。"