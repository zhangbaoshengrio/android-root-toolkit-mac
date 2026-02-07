import tkinter as tk
from tkinter import filedialog, messagebox, ttk, scrolledtext
import subprocess
import threading
import shutil
import os
import time
import sys  # 新增: 用于打包后的路径判断

# ================= 配置区域 =================
# 如果你的 adb/fastboot 不在环境变量里，且不在脚本同级目录的 platform-tools 里
# 请在这里手动填入绝对路径
CUSTOM_ADB_PATH = "" 
CUSTOM_FASTBOOT_PATH = ""
DUMPER_PATH = shutil.which("payload-dumper-go") or "payload-dumper-go"
# ===========================================

class RootToolApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Android Root 全能工具箱 (Mac/PC)")
        self.root.geometry("700x750")
        
        # 样式设置
        style = ttk.Style()
        style.configure("TButton", font=("Arial", 11), padding=5)
        style.configure("Bold.TLabel", font=("Arial", 10, "bold"))

        # 创建选项卡
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        # Tab 1: 提取
        self.tab_extract = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_extract, text="Step 1: 提取镜像")
        self.init_extract_tab()

        # Tab 2: 刷机
        self.tab_flash = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_flash, text="Step 2: 一键刷机")
        self.init_flash_tab()

    # ================= 工具函数 =================
    def get_tool_path(self, tool_name):
        """智能查找 adb 或 fastboot (兼容打包后的 .app)"""
        # 1. 优先使用配置的路径
        if tool_name == "adb" and CUSTOM_ADB_PATH: return CUSTOM_ADB_PATH
        if tool_name == "fastboot" and CUSTOM_FASTBOOT_PATH: return CUSTOM_FASTBOOT_PATH
        
        # 2. 确定基础路径 (兼容脚本运行和 PyInstaller 打包运行)
        if getattr(sys, 'frozen', False):
            # 打包环境
            base_path = os.path.dirname(sys.executable)
            # Mac .app 特殊结构修正 (从 Contents/MacOS 往上跳)
            if "Contents/MacOS" in base_path:
                base_path = os.path.abspath(os.path.join(base_path, "../../.."))
        else:
            # 脚本环境
            base_path = os.getcwd()

        # 3. 查找脚本/软件同级目录下的 platform-tools
        local_tool = os.path.join(base_path, "platform-tools", tool_name)
        if os.path.exists(local_tool): return local_tool
        
        # 4. 系统环境
        if shutil.which(tool_name): return tool_name
        
        return None

    def log(self, message, tag="INFO"):
        """输出日志到 Tab 2 的控制台"""
        self.console.config(state="normal")
        if tag == "SUCCESS":
            self.console.insert("end", f"[√] {message}\n", "success")
        elif tag == "ERROR":
            self.console.insert("end", f"[X] {message}\n", "error")
        elif tag == "WAIT":
            self.console.insert("end", f"[...] {message}\n", "wait")
        else:
            self.console.insert("end", f"[*] {message}\n")
        self.console.see("end")
        self.console.config(state="disabled")

    # ================= Tab 1: 提取功能 =================
    def init_extract_tab(self):
        frame = tk.Frame(self.tab_extract, padx=10, pady=10)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Payload.bin 提取助手", font=("Arial", 16, "bold")).pack(pady=10)
        
        # 路径选择
        self.payload_path = tk.StringVar()
        tk.Button(frame, text="选择 payload.bin", command=self.select_payload).pack(fill="x", pady=5)
        tk.Entry(frame, textvariable=self.payload_path, state="readonly").pack(fill="x", pady=5)
        
        self.output_path = tk.StringVar()
        tk.Button(frame, text="选择输出文件夹", command=self.select_output).pack(fill="x", pady=5)
        tk.Entry(frame, textvariable=self.output_path, state="readonly").pack(fill="x", pady=5)

        tk.Label(frame, text="提示：此页面用于提取 init_boot.img，提取后请切换到 '一键刷机' 页面。", fg="gray").pack(pady=20)
        
        self.btn_extract_init = tk.Button(frame, text="提取 init_boot.img (推荐)", command=self.run_extract_init, bg="#007AFF", fg="black")
        self.btn_extract_init.pack(pady=10, ipady=5, fill="x")

    def select_payload(self):
        p = filedialog.askopenfilename(filetypes=[("Bin", "*.bin")])
        if p: 
            self.payload_path.set(p)
            if not self.output_path.get():
                self.output_path.set(os.path.dirname(p)) # 默认输出到同级

    def select_output(self):
        p = filedialog.askdirectory()
        if p: self.output_path.set(p)

    def run_extract_init(self):
        if not self.payload_path.get() or not self.output_path.get():
            messagebox.showwarning("提示", "请先选择文件和输出路径")
            return
        
        def _run():
            # 兼容 Mac/PC 的调用
            cmd = [DUMPER_PATH, "-p", "init_boot", "-o", self.output_path.get(), self.payload_path.get()]
            try:
                subprocess.run(cmd, check=True)
                messagebox.showinfo("成功", "提取完成！请切换到 'Step 2' 页面继续。")
            except Exception as e:
                messagebox.showerror("失败", f"提取出错: {str(e)}\n请检查 payload-dumper-go 是否在路径中。")
        
        threading.Thread(target=_run).start()

    # ================= Tab 2: 自动化刷机功能 =================
    def init_flash_tab(self):
        frame = tk.Frame(self.tab_flash, padx=10, pady=10)
        frame.pack(fill="both", expand=True)

        # 1. 警告区域
        warn_frame = tk.LabelFrame(frame, text="⚠️ 风险提示", fg="red")
        warn_frame.pack(fill="x", pady=5)
        tk.Label(warn_frame, text="1. 必须已解锁 Bootloader (BL)。\n2. 刷机有风险，请务必备份重要数据！\n3. 仅限 init_boot 分区 (Android 13+)。", justify="left", fg="red").pack(anchor="w", padx=5, pady=5)

        # 2. 文件选择
        file_frame = tk.LabelFrame(frame, text="准备工作")
        file_frame.pack(fill="x", pady=10)
        
        tk.Label(file_frame, text="待修补文件 (init_boot.img):").grid(row=0, column=0, sticky="w")
        self.flash_img_path = tk.StringVar()
        tk.Entry(file_frame, textvariable=self.flash_img_path, width=40).grid(row=0, column=1, padx=5)
        tk.Button(file_frame, text="选择文件", command=self.select_flash_img).grid(row=0, column=2)

        # 3. 控制台日志
        log_frame = tk.LabelFrame(frame, text="执行日志")
        log_frame.pack(fill="both", expand=True, pady=5)
        
        self.console = scrolledtext.ScrolledText(log_frame, height=15, bg="black", fg="white", font=("Monaco", 10))
        self.console.pack(fill="both", expand=True, padx=5, pady=5)
        # 配置日志颜色
        self.console.tag_config("success", foreground="#00FF00") 
        self.console.tag_config("error", foreground="#FF0000")   
        self.console.tag_config("wait", foreground="#FFFF00")    

        # 4. 开始按钮
        self.btn_start_flash = tk.Button(frame, text="开始全自动流程 (Root)", command=self.start_automation, bg="red", fg="black", font=("Arial", 12, "bold"))
        self.btn_start_flash.pack(fill="x", ipady=10, pady=5)

    def select_flash_img(self):
        p = filedialog.askopenfilename(filetypes=[("Image", "*.img")])
        if p: self.flash_img_path.set(p)

    def start_automation(self):
        img_path = self.flash_img_path.get()
        if not img_path:
            messagebox.showerror("错误", "请先选择提取好的 init_boot.img 文件")
            return

        adb = self.get_tool_path("adb")
        fastboot = self.get_tool_path("fastboot")

        if not adb or not fastboot:
            self.log("未找到 adb 或 fastboot 工具！", "ERROR")
            self.log("请将 'platform-tools' 文件夹放到脚本或 App 同级目录下。", "ERROR")
            messagebox.showerror("环境缺失", "找不到 adb 或 fastboot，无法继续。")
            return

        # 在新线程运行，避免卡死界面
        threading.Thread(target=self.run_process, args=(adb, fastboot, img_path)).start()

    def run_process(self, adb, fastboot, img_path):
        self.btn_start_flash.config(state="disabled")
        self.console.config(state="normal")
        self.console.delete(1.0, "end") # 清空日志
        self.console.config(state="disabled")

        try:
            # === Step 1: 检查连接 ===
            self.log("Step 1: 检查设备连接...")
            # Mac 不需要 shell=True
            res = subprocess.run([adb, "devices"], capture_output=True, text=True)
            if "device" not in res.stdout or "\tdevice" not in res.stdout:
                raise Exception("未检测到设备，请开启 USB 调试并连接手机。")
            self.log("设备已连接。", "SUCCESS")

            # === Step 2: 推送文件 ===
            self.log("Step 2: 推送 init_boot.img 到手机...")
            target_path = "/sdcard/Download/init_boot_raw.img"
            subprocess.run([adb, "push", img_path, target_path], check=True)
            self.log(f"推送成功: {target_path}", "SUCCESS")

            # === Step 3: 等待用户修补 ===
            self.log("Step 3: 等待用户在 Magisk 中修补...", "WAIT")
            self.log(">>> 请打开手机上的 Magisk App", "WAIT")
            self.log(">>> 点击 '安装' -> '选择并修补一个文件'", "WAIT")
            self.log(">>> 选择刚才传入的 'init_boot_raw.img'", "WAIT")
            self.log(">>> ⚠️ 修补完成后，请回到电脑点击'是'。", "WAIT")

            # 弹窗阻塞
            is_done = messagebox.askyesno("人工操作", "请在手机 Magisk 上完成修补。\n\n修补完成了吗？")
            if not is_done:
                raise Exception("用户取消操作")

            # === Step 4: 自动拉取修补文件 (Python 筛选修复版) ===
            self.log("Step 4: 搜索 magisk_patched 文件...")
            
            # 使用 ls -t 列出所有文件，然后由 Python 筛选，解决 ADB 通配符兼容问题
            cmd_ls = [adb, "shell", "ls", "-t", "/sdcard/Download/"]
            res = subprocess.run(cmd_ls, capture_output=True, text=True)
            
            if res.returncode != 0:
                raise Exception("无法读取手机下载目录，请检查手机是否锁定或权限不足。")

            lines = res.stdout.splitlines()
            target_filename = None
            
            # 在返回的文件列表中寻找符合条件的文件
            for line in lines:
                line = line.strip()
                # 寻找以 magisk_patched 开头且以 .img 结尾的文件
                if line.startswith("magisk_patched") and line.endswith(".img"):
                    target_filename = line
                    break # ls -t 是按时间倒序的，找到的第一个就是最新的
            
            if not target_filename:
                 raise Exception("未找到 magisk_patched 文件！\n请确认文件确实保存在 /sdcard/Download/ 目录下。")

            full_phone_path = f"/sdcard/Download/{target_filename}"
            local_patched_file = os.path.join(os.getcwd(), "magisk_patched_auto.img")
            
            self.log(f"锁定文件: {full_phone_path}", "SUCCESS")
            
            # 拉取
            subprocess.run([adb, "pull", full_phone_path, local_patched_file], check=True)
            self.log(f"已下载到电脑: {local_patched_file}", "SUCCESS")

            # 清理手机垃圾
            try:
                subprocess.run([adb, "shell", "rm", target_path], capture_output=True)
                subprocess.run([adb, "shell", "rm", full_phone_path], capture_output=True)
            except:
                pass 

            # === Step 5: 重启到 Bootloader ===
            self.log("Step 5: 正在重启到 Bootloader 模式...", "WAIT")
            subprocess.run([adb, "reboot", "bootloader"])
            
            self.log("等待 Fastboot 设备上线...")
            device_found = False
            for i in range(30): 
                time.sleep(1)
                res = subprocess.run([fastboot, "devices"], capture_output=True, text=True)
                if "fastboot" in res.stdout:
                    device_found = True
                    break
            
            if not device_found:
                raise Exception("Fastboot 设备检测超时！请检查驱动或数据线连接。")
            self.log("Fastboot 设备已连接。", "SUCCESS")

            # === Step 6: 刷入文件 ===
            self.log("Step 6: 开始刷入 init_boot 分区...", "WAIT")
            self.log(f"正在刷入: {local_patched_file}")
            
            cmd_flash = [fastboot, "flash", "init_boot", local_patched_file]
            flash_res = subprocess.run(cmd_flash, capture_output=True, text=True)
            
            # 记录详细日志
            if flash_res.stderr: self.log(flash_res.stderr.strip())
            if flash_res.stdout: self.log(flash_res.stdout.strip())

            if flash_res.returncode != 0:
                raise Exception("刷入失败，请检查 Bootloader 是否已解锁。")
            self.log("刷入成功！", "SUCCESS")

            # === Step 7: 重启系统 ===
            self.log("Step 7: 正在重启手机...", "WAIT")
            subprocess.run([fastboot, "reboot"])
            self.log("====== 全部完成！恭喜获得 Root 权限 ======", "SUCCESS")
            messagebox.showinfo("恭喜", "Root 流程执行完毕，手机正在重启。")

        except Exception as e:
            self.log(f"流程终止: {str(e)}", "ERROR")
            messagebox.showerror("错误", str(e))
        
        finally:
            self.btn_start_flash.config(state="normal")

if __name__ == "__main__":
    root = tk.Tk()
    app = RootToolApp(root)
    root.mainloop()