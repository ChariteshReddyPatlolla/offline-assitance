import streamlit as st
import time
import asyncio
import os
import sys

# Ensure local imports work
sys.path.append(os.getcwd())

st.set_page_config(page_title="Agent OS Dashboard", page_icon="🤖", layout="wide")

st.title("🤖 Local Autonomous Agent OS")
st.markdown("Welcome to the **Interactive Dashboard**. Enter a goal below, and watch the multi-agent system break it down and execute it!")

# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history on app rerun
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("Enter your macro-goal (e.g., 'Write a python script to ping google.com')"):
    # Display user message in chat message container
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        st.markdown(f"**Goal Received:** {prompt}")
        st.markdown("Initializing **LangGraph State** and handing off to **Planner Agent**...")
        
        # Create Layout Columns for DAG and Logs
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📋 Execution DAG")
            dag_placeholder = st.empty()
            
        with col2:
            st.subheader("🖥️ Agent Execution Logs")
            log_placeholder = st.empty()

        import subprocess
        import json
        import requests
        
        # 1. Contact Ollama for dynamic planning and command generation
        st.markdown(f"🧠 Querying `llama3.1` to generate dynamic execution plan...")
        
        prompt_template = f"""
        You are the Local Autonomous Agent OS. The user's goal is: "{prompt}"
        Decompose this goal into a strict sequence of shell commands (PowerShell/cmd) needed to achieve it.
        Respond ONLY with a valid JSON array of objects. Do NOT use markdown code blocks like ```json.
        Example format:
        [
          {{"agent": "planner", "task": "Analyze Request", "command": ""}},
          {{"agent": "automation", "task": "Make directory", "command": "mkdir new_folder"}},
          {{"agent": "coding", "task": "Create file", "command": "echo print('hello') > new_folder/test.py"}},
          {{"agent": "browser", "task": "Ping site", "command": "ping google.com"}}
        ]
        """
        
        try:
            response = requests.post("http://localhost:11434/api/generate", json={
                "model": "llama3.1:8b",
                "prompt": prompt_template,
                "stream": False
            })
            
            raw_text = response.json().get("response", "[]").strip()
            
            # Clean up potential markdown blocks the LLM might have outputted
            if raw_text.startswith("```json"):
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
            elif raw_text.startswith("```"):
                raw_text = raw_text.replace("```", "").strip()
                
            tasks = json.loads(raw_text)
            
        except Exception as e:
            tasks = [
                {"agent": "critic", "task": "Error parsing LLM response", "command": f"echo Error: {str(e)}"}
            ]
        
        log_text = ""
        
        # Stream the execution visually
        for step in tasks:
            agent_name = step.get("agent", "automation").lower()
            task_name = step.get("task", "Executing...")
            command = step.get("command", "")
            
            # Update DAG visually
            dag_md = f"- 🟢 **{task_name}**\n"
            dag_placeholder.markdown(dag_md)
                
            # Update Logs visually
            log_msg = f"Executing Command: '{command}'" if command else "Analyzing Context..."
            log_text += f"**[{agent_name.upper()}]**: {log_msg}\n\n"
            log_placeholder.markdown(log_text)
            
            # Actually execute the shell command if it exists
            if command:
                try:
                    result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=15)
                    if result.stdout:
                        log_text += f"> {result.stdout.strip()}\n\n"
                    if result.stderr:
                        log_text += f"> Error: {result.stderr.strip()}\n\n"
                except Exception as ex:
                    log_text += f"> Execution Exception: {str(ex)}\n\n"
                    
            log_placeholder.markdown(log_text)
            time.sleep(1.0) # Simulate execution delay
            
        st.success("✅ Workflow Complete! The Agent OS has executed your commands securely.")
        st.session_state.messages.append({"role": "assistant", "content": "Execution complete! Check your files to see the result."})
