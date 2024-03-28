import shutil
import os

def backup_files(file_paths, destination_directory):
    # 检查目标目录是否存在，不存在则创建
    if not os.path.exists(destination_directory):
        os.makedirs(destination_directory)

    for source_file_path in file_paths:
        # 检查源文件是否存在
        if os.path.exists(source_file_path):
            # 获取文件名
            file_name = os.path.basename(source_file_path)

            # 构建目标文件路径
            destination_file_path = os.path.join(destination_directory, file_name)

            # 检查目标文件是否存在，存在则删除
            if os.path.exists(destination_file_path):
                os.remove(destination_file_path)

            # 拷贝文件，覆盖已存在的文件
            shutil.copy2(source_file_path, destination_file_path)
            print(f"文件 '{file_name}' 备份到 '{destination_directory}'")
        else:
            print(f"文件 '{source_file_path}' 没有找到. 跳过.")

def backup_dir(source_path, destination_directory):
    # 检查目标目录是否存在，不存在则创建
    if not os.path.exists(destination_directory):
        os.makedirs(destination_directory)

    # 构建目标路径
    destination_path = os.path.join(destination_directory, os.path.basename(source_path))

    try:
        # 检查源路径是文件还是文件夹
        if os.path.isfile(source_path):
            # 如果是文件，检查目标文件是否存在，存在则删除
            if os.path.exists(destination_path):
                os.remove(destination_path)

            # 使用 shutil.copy2 进行文件拷贝
            shutil.copy2(source_path, destination_path)
            print(f"文件 '{source_path}' 备份到 '{destination_directory}'")
        elif os.path.isdir(source_path):
            # 如果是文件夹，检查目标文件夹是否存在，存在则删除
            if os.path.exists(destination_path):
                shutil.rmtree(destination_path)

            # 使用 shutil.copytree 进行文件夹拷贝
            shutil.copytree(source_path, destination_path)
            print(f"文件夹 '{source_path}' 备份到 '{destination_directory}'")
        else:
            print(f"Unsupported source type: '{source_path}'")
    except Exception as e:
        print(f"Error during backup: {e}")

# 获取当前脚本所在的绝对路径
current_directory = os.path.abspath(os.path.dirname(__file__))
# 示例用法
file_paths_to_backup = [
    os.path.join(current_directory, "config.json")
]
dir_path_to_backup = os.path.join(current_directory, "data")
dir_path_to_backup2 = os.path.join(current_directory, "out")

destination_directory_path = os.path.join(current_directory, "backup")  # 替换为实际的备份目录路径

backup_files(file_paths_to_backup, destination_directory_path)
backup_dir(dir_path_to_backup, destination_directory_path)
backup_dir(dir_path_to_backup2, destination_directory_path)

print("运行结束")
