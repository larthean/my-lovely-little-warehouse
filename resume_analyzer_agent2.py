#!/usr/bin/env python3
"""
简历分析智能体
"""
import streamlit as st
from openai import OpenAI

Api_BASE_url = "https://api.siliconflow.cn/v1"
TARGET_POSITIONS = ["岗位", "python开发工程师", "产品经理", "数据分析师", "UI/UX设计师"]

def extract_file_content(uploaded_file):
    """
    从上传的文件中提取内容
    """
    if not uploaded_file:
        return None
    file_content = uploaded_file.read()
    if uploaded_file.type == "text/plain":
        return file_content.decode("utf-8")
    else:
        return "演示模式"

def get_resume_content(uploaded_file, resume_test):
    """
    获取简历内容
    """
    if uploaded_file:
        resume_content = extract_file_content(uploaded_file)
    elif resume_test:
        resume_content = resume_test
    else:
        return None
    return resume_content

def analyze_resume_with_ai(resume_text, target_position, api_key):
    """
    分析简历内容
    """
    if not api_key or api_key.strip() == "":
        return "请先配置OpenAI API密钥"
    
    client = OpenAI(
        api_key=api_key,
        base_url=Api_BASE_url,
    )
    
    prompt = f"作为专业的HR顾问，请分析以下简历，针对{target_position}岗位进行评估，判断其是否符合目标岗位要求：{resume_text}\n请提供1，总体评分（0-100分）2，详细分析和改进建议3，核心优势和发展建议 要求评分和建议完全基于简历内容，个性化分析，避免模板化回复"
    
    response = client.chat.completions.create(
        model="Qwen/Qwen2.5-72B-Instruct",
        messages=[
            {"role": "system", "content": "你是一个专业的简历分析顾问,根据简历内容给出客观个性化的分析和建议"},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1500,
    )
    
    return response.choices[0].message.content

def handle_analyze_click(uploaded_file, resume_test, target_position, api_key):
    """
    处理分析按钮点击事件
    """
    content = get_resume_content(uploaded_file, resume_test)
    if not content:
        st.warning("请输入简历内容或上传简历文件")
        return
    
    with st.spinner("正在分析..."):
        analysis_result = analyze_resume_with_ai(content, target_position, api_key)
        st.session_state.analysis_result = analysis_result
        st.session_state.target_position = target_position
        st.success("分析完成")
        st.write(analysis_result)

def main():
    """
    主函数
    """
    st.set_page_config(page_title="简历分析智能体", page_icon=":memo:", layout="wide")
    
    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    
    with st.sidebar:
        st.markdown("## 智能分析Agent")
        st.markdown("### API配置")
        api_key = st.text_input("OPENAI API密钥", type="password", placeholder="请输入OPENAI API密钥", help="在硅基流动官网获取")
        if api_key:
            st.success("API密钥配置成功")    
        else:
            st.warning("请配置OPENAI API密钥")
        
        st.markdown("### 系统功能")
        st.markdown("简历上传分析\nAI智能评分\n个性化建议\n职业规划指导")
    
    st.title("简历分析智能体")
    st.markdown("### 基于AI的专业简历分析与职业指导平台")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("#### 上传简历")
        target_position = st.selectbox("选择目标岗位", TARGET_POSITIONS, help="请选择要应聘的岗位类型")
        uploaded_file = st.file_uploader("上传简历文件(支持TXT)", type=["txt"])
        
        st.markdown("#### 输入简历内容")
        resume_test = st.text_area("或直接输入简历内容", height=200, help="输入要分析的简历内容")
        
        if st.button("开始AI分析", type="primary", use_container_width=True):
            handle_analyze_click(uploaded_file, resume_test, target_position, api_key)
    
    with col2:
        st.markdown("#### 分析结果")
        if st.session_state.analysis_result:
            st.markdown(f"### 目标岗位：{st.session_state.get('target_position', '未选择')}")
            with st.container():
                st.markdown(st.session_state.analysis_result)
                
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button("复制结果", use_container_width=True):
                        st.info("请手动复制")
                with col_b:
                    if st.button("重新分析", use_container_width=True):
                        st.session_state.analysis_result = None
                        st.rerun()
        else:
            st.info("""
            #### AI智能分析
            系统特色
            - 个性化分析
            - 智能评分
            - 针对性建议
            - 职业规划

            使用说明：
            1. 配置API密钥
            2. 选择目标岗位
            3. 上传简历或输入内容
            4. 点击开始分析
            """)

if __name__ == "__main__":
    main()
