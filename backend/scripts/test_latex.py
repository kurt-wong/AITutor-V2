import re

# 测试 LaTeX 格式移除
# 实际格式：$12\text{—}18$ 其中 \t 是 tab (0x09)
d = 'Ages:$12\ttext{—}18$'
print('Before:', repr(d))

# 提取 $...$ 中的内容，移除 LaTeX 命令
def clean_latex(m):
    content = m.group(1)
    # 移除 \text{...} → 内容
    content = re.sub(r'text\{([^}]*)\}', r'\1', content)
    return content

d = re.sub(r'\$([^$]*)\$', clean_latex, d)
print('After:', repr(d))
