import os

folder_path = "ikaros"  # 替换为您要获取文件名的文件夹路径

# 使用os模块列出文件夹内的所有文件
file_names = os.listdir(folder_path)

# 打印文件名列表
for file_name in file_names:
    print(f'"data/闲时任务/音频/{folder_path}/{file_name}",')
