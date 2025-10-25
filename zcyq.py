#!/usr/bin/env python3
"""
智策云擎 - 基于AI的专业分析与优化指导平台

该系统使用先进的AI模型对用户提交的内容进行专业分析，
提供个性化的评分、建议和优化方案。
"""
import streamlit as st
import json
import time
import hashlib
from datetime import datetime
from openai import OpenAI
import traceback

# 全局配置
Api_BASE_url = "https://api.siliconflow.cn/v1"
TARGET_POSITIONS = ["职业规划", "营销方案", "数据分析师"]
MAX_HISTORY_RECORDS = 10  # 最大历史记录数
CACHE_EXPIRY_TIME = 3600  # 缓存过期时间（秒）

def init_session_state():
    """
    初始化会话状态
    """
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "target_position" not in st.session_state:
        st.session_state.target_position = None
    if "analysis_history" not in st.session_state:
        st.session_state.analysis_history = []
    if "cache" not in st.session_state:
        st.session_state.cache = {}


def extract_file_content(uploaded_file):
    """
    从上传的文件中提取内容，支持多种文件格式
    """
    if not uploaded_file:
        return None, None
        
    file_content = uploaded_file.read()
    file_type = uploaded_file.type
    file_name = uploaded_file.name
    
    try:
        if file_type == "text/plain" or file_name.endswith(".txt"):
            return file_content.decode("utf-8"), "文本文件"
        elif file_type == "application/json" or file_name.endswith(".json"):
            json_data = json.loads(file_content.decode("utf-8"))
            return json.dumps(json_data, ensure_ascii=False, indent=2), "JSON文件"
        elif file_type == "application/vnd.ms-excel" or \
             file_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" or \
             file_name.endswith(".csv"):
            # 简单文本处理，实际应用中可使用pandas进行更复杂的解析
            return "表格文件内容（需使用pandas进行详细解析）", "表格文件"
        else:
            # 对于不支持的文件类型，尝试以文本形式读取
            try:
                return file_content.decode("utf-8", errors="replace"), "未知格式（已尝试文本解析）"
            except:
                return "无法解析的文件格式", "不支持的文件类型"
    except Exception as e:
        return f"文件解析错误: {str(e)}", "错误"


def get_cache_key(content, target_position):
    """
    生成缓存键
    """
    combined = f"{content[:1000]}:{target_position}"
    return hashlib.md5(combined.encode()).hexdigest()


def check_cache(cache_key):
    """
    检查缓存是否有效
    """
    if cache_key in st.session_state.cache:
        cache_data = st.session_state.cache[cache_key]
        if time.time() - cache_data["timestamp"] < CACHE_EXPIRY_TIME:
            return cache_data["result"]
    return None


def update_cache(cache_key, result):
    """
    更新缓存
    """
    st.session_state.cache[cache_key] = {
        "result": result,
        "timestamp": time.time()
    }


def update_history(content, target_position, result):
    """
    更新分析历史记录
    """
    history_item = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "target_position": target_position,
        "content_preview": content[:50] + "..." if len(content) > 50 else content,
        "result": result
    }
    
    # 添加到历史记录开头
    st.session_state.analysis_history.insert(0, history_item)
    
    # 限制历史记录数量
    if len(st.session_state.analysis_history) > MAX_HISTORY_RECORDS:
        st.session_state.analysis_history = st.session_state.analysis_history[:MAX_HISTORY_RECORDS]


def analyze_content_with_ai(content, target_position, api_key):
    """
    使用AI分析内容，带缓存机制和错误处理
    """
    if not api_key or api_key.strip() == "":
        return "请先配置OpenAI API密钥"
    
    # 生成缓存键并检查缓存
    cache_key = get_cache_key(content, target_position)
    cached_result = check_cache(cache_key)
    if cached_result:
        return cached_result, True  # 第二个参数表示是否来自缓存
    
    try:
        client = OpenAI(
            api_key=api_key,
            base_url=Api_BASE_url,
        )
        
        # 根据不同的目标类别定制分析提示
        system_prompts = {
            "职业规划": "你是一名拥有10年经验的资深职业规划顾问，擅长分析简历和职业发展路径，提供专业、具体且可行的建议。",
            "营销方案": "你是一名顶尖的营销策划专家，拥有丰富的行业经验，能够深入分析营销方案的可行性、创新性和市场价值。",
            "数据分析师": "你是一名资深的数据分析师，精通数据驱动的决策方法，擅长评估数据分析能力和项目质量。"
        }
        
        system_prompt = system_prompts.get(target_position, "你是一名拥有10年经验的职业规划顾问、数据分析师和营销策划专家")
        
        # 定制化分析提示
        prompt = f"请针对{target_position}对以下内容进行专业评估：\n\n{content}\n\n请提供：\n1. 总体评分（0-100分）\n2. 详细分析和改进建议\n3. 核心优势和发展建议\n4. 差异化优势分析\n"
        
        # 根据不同类别添加特定要求
        if target_position == "营销方案":
            prompt += "5. 针对方案中存在的问题提供可行性修改建议\n6. 市场价值定位分析\n"
        elif target_position == "职业规划":
            prompt += "5. 职业发展路径规划\n6. 竞争力提升建议\n"
        elif target_position == "数据分析师":
            prompt += "5. 技术能力评估\n6. 项目质量分析\n"
        
        prompt += "\n要求评分和建议完全基于提交内容，提供个性化、具体且可行的分析，避免模板化回复。"
        
        response = client.chat.completions.create(
            model="Qwen/Qwen2.5-72B-Instruct",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7,  # 稍微提高温度以增加回复的多样性
            top_p=0.9  # 控制生成内容的多样性
        )
        
        result = response.choices[0].message.content
        
        # 更新缓存
        update_cache(cache_key, result)
        
        return result, False
    
    except Exception as e:
        error_detail = traceback.format_exc()
        return f"AI分析失败: {str(e)}\n\n详细错误:\n{error_detail}", False

def handle_analyze_click(uploaded_file, resume_test, target_position, api_key):
    """
    处理分析按钮点击事件，包含文件处理、内容分析和历史记录更新
    """
    # 获取内容
    content = None
    content_source = ""
    
    if uploaded_file:
        content, file_type = extract_file_content(uploaded_file)
        content_source = f"上传的{file_type}"
    elif resume_test:
        content = resume_test
        content_source = "输入的内容"
    
    if not content:
        st.warning("请输入类别内容或上传文件")
        return
    
    # 验证内容长度
    if len(content.strip()) < 10:
        st.warning("内容过短，请提供足够的信息进行分析")
        return
    
    with st.spinner(f"正在分析{content_source}..."):
        try:
            # 调用AI分析（带缓存机制）
            analysis_result, from_cache = analyze_content_with_ai(content, target_position, api_key)
            
            # 更新会话状态
            st.session_state.analysis_result = analysis_result
            st.session_state.target_position = target_position
            st.session_state.last_analysis_content = content
            
            # 更新历史记录（仅当非缓存结果时）
            if not from_cache and not analysis_result.startswith("请先配置OpenAI API密钥") and not analysis_result.startswith("AI分析失败"):
                update_history(content, target_position, analysis_result)
            
            # 显示分析完成消息
            if from_cache:
                st.success("分析完成（来自缓存）")
            else:
                st.success("分析完成")
                
        except Exception as e:
            st.error(f"处理分析请求时出错: {str(e)}")
            return

def main():
    """
    主函数 - 智策云擎AI分析平台入口
    集成了AI分析、历史记录、结果导出等功能
    """
    # 页面配置
    st.set_page_config(
        page_title="智策云擎 - AI智能分析平台",
        page_icon=":chart_with_upwards_trend:",
        layout="wide"
    )
    
    # 初始化会话状态
    init_session_state()
    
    # 侧边栏 - 系统配置和信息
    with st.sidebar:
        # API配置
        st.markdown("## :key: API配置")
        api_key = st.text_input(
            "OPENAI API密钥",
            type="password",
            placeholder="请输入OPENAI API密钥",
            help="在硅基流动官网获取API密钥"
        )
        
        if api_key:
            st.success("✅ API密钥配置成功")
        else:
            st.warning("⚠️ 请配置OPENAI API密钥")
        
        # 系统功能介绍
        st.markdown("## :star: 系统功能")
        st.markdown("- 🤖 AI智能评分与分析")
        st.markdown("- 💡 个性化专业建议")
        st.markdown("- ⏱️ 智能缓存加速响应")
        st.markdown("- 📋 分析历史记录管理")
        
        # 缓存统计信息
        st.markdown("## :gear: 系统状态")
        cache_size = len(st.session_state.get("cache", {}))
        history_count = len(st.session_state.get("analysis_history", []))
        st.markdown(f"- 📦 缓存条目: {cache_size}")
        st.markdown(f"- 📝 历史记录: {history_count}")
        
        # 清除缓存按钮
        if st.button("🗑️ 清除缓存", use_container_width=True):
            st.session_state.cache = {}
            st.session_state.cache_timestamp = {}
            st.success("缓存已清除")
    
    # 主页面标题
    st.title("智策云擎")
    st.markdown("### 基于AI的专业分析与优化指导平台")
    
    # 主内容区布局
    tab1, tab2 = st.tabs(["🔍 AI分析", "📊 历史记录"])
    
    # 分析标签页
    with tab1:
        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            # 输入区域
            with st.container(border=True):
                st.markdown("#### 📥 上传分析材料")
                target_position = st.selectbox(
                    "🔖 选择目标类别", 
                    TARGET_POSITIONS, 
                    help="请选择要分析的项目类别"
                )
                
                st.markdown("##### 上传文件")
                uploaded_file = st.file_uploader(
                    "支持多种文本格式", 
                    type=["txt", "md", "json", "csv"]
                )
                
                st.markdown("##### 或直接输入")
                resume_test = st.text_area(
                    "输入要分析的内容", 
                    height=200,
                    placeholder="请在此处粘贴您的内容...",
                    help="输入要分析的内容"
                )
                
                # 分析按钮
                if st.button("🚀 开始AI分析", type="primary", use_container_width=True):
                    handle_analyze_click(uploaded_file, resume_test, target_position, api_key)
        
        with col2:
            # 结果显示区域
            with st.container(border=True):
                st.markdown("#### 📊 分析结果")
                
                if st.session_state.analysis_result:
                    # 显示分析结果标题
                    st.markdown(f"### 项目类别：{st.session_state.get('target_position', '未选择')}")
                    
                    # 结果内容
                    with st.expander("查看详细分析", expanded=True):
                        st.markdown(st.session_state.analysis_result)
                    
                    # 结果操作按钮
                    if st.button("🔄 重新分析", use_container_width=True):
                        st.session_state.analysis_result = None
                        st.session_state.target_position = None
                        st.rerun()
                else:
                    # 空状态提示
                    st.info("""
                    #### 🤖 AI智能分析平台
                    
                    **系统特色**
                    - 🎯 个性化专业分析
                    - 🌟 精准评分系统
                    - 📝 详细改进建议
                    - 🚀 优化路径规划

                    **使用流程**:
                    1. 配置API密钥
                    2. 选择分析类别
                    3. 上传文件或输入内容
                    4. 点击开始分析
                    """)
    
    # 历史记录标签页
    with tab2:
        st.markdown("#### 📊 分析历史记录")
        
        if st.session_state.analysis_history:
            # 显示历史记录列表
            for i, record in enumerate(reversed(st.session_state.analysis_history)):
                with st.expander(f"{record['timestamp']} - {record['target_position']}", expanded=False):
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown("**内容摘要**: ")
                        st.markdown(record['content_preview'])
                        
                        if st.button("查看完整结果", key=f"view_{i}"):
                            st.session_state.analysis_result = record['result']
                            st.session_state.target_position = record['target_position']
                            st.rerun()
                    with col2:
                        st.markdown("**操作**:")
                        if st.button("删除记录", key=f"delete_{i}", use_container_width=True, type="secondary"):
                            st.session_state.analysis_history.pop(len(st.session_state.analysis_history) - 1 - i)
                            st.rerun()
        else:
            st.info("暂无分析历史记录")

if __name__ == "__main__":
    main()
