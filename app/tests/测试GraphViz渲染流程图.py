from graphviz import Digraph
import os

# 核心修复：手动指定Graphviz的dot.exe路径（替换为你的安装路径）
# 常见路径：C:\Program Files\Graphviz\bin\dot.exe 或 C:\Graphviz\bin\dot.exe
os.environ["PATH"] += os.pathsep + r"C:\Program Files\Graphviz\bin"

# 创建有向图对象（修复边定义错误：原代码有CD但无D节点）
g = Digraph()

# 添加节点和边（修复错误：原代码g.edges(['AB', 'BC', 'CD'])中D节点不存在）
g.node('A', 'Start')
g.node('B', 'Process')
g.node('C', 'End')
g.edges(['AB', 'BC'])  # 移除CD，仅保留存在的节点边

# 设置图形属性
g.attr(rankdir='LR', size='8,5')  # 从左到右布局
g.node_attr.update(color='lightblue2', style='filled')
g.edge_attr.update(color='gray')

output_dir = '../graph/test-output'
os.makedirs(output_dir, exist_ok=True)  # 自动创建目录，避免路径不存在报错

# 渲染并保存为PNG（cleanup=True 清理临时文件）
g.render(os.path.join(output_dir, 'flowchart'), format='png', cleanup=True, view=True)

if __name__ == "__main__":
    g.render('test', format='png', cleanup=True)
    print("流程图生成成功！")