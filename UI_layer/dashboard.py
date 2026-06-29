import argparse
import ast
import csv
import gzip
import heapq
import json
import os
import re
import subprocess
import sys
from datetime import datetime, date
import pandas as pd
import streamlit as st
st.markdown(
    """
<style>
.stApp, [data-testid="stAppViewContainer"] {
        background-color: #080710 !important; 
        background-image: 
            radial-gradient(circle at 20% 30%, rgba(188, 150, 230, 0.15) 0%, transparent 40%), 
            radial-gradient(circle at 80% 70%, rgba(137, 207, 240, 0.12) 0%, transparent 45%), 
            radial-gradient(circle at 50% 10%, rgba(230, 204, 150, 0.08) 0%, transparent 35%); 
        background-attachment: fixed;
        position: relative;
        overflow: hidden;
    }
@import url('https://fonts.googleapis.com/css2?family=Sora:wght=700&family=Inter:wght=400;600&display=swap');
.title{
    font-family: 'Sora', sans-serif!important;
    font-weight:bold;
    font-size: 4.5rem!important;           
    color: #BC96E6!important;
    text-align:center;
    background: linear-gradient(
            to right, 
            #BC96E6 0%,    
            #BC96E6 40%,   
            #FFFFFF 50%,  
            #BC96E6 60%,   
            #BC96E6 100%  
        );
    background-size:200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shine 2s linear infinite;
}
@keyframes shine {
    0%{ background-position: 200% center;}
    100%{ background-position: -200% center;}
}
.sliding-text {
    font-family: 'Inter', sans-serif;
    font-size: 14px;
    font-weight: 600;
    color: #73C2BE;   
    background: rgba(188, 150, 230, 0.05);
    border: 1px solid rgba(188, 150, 230, 0.15);
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 25px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='title'> CVScout </h1>", unsafe_allow_html=True)

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)

RANK_SCRIPT_PATH = os.path.join(ROOT_DIR, "rank.py")
PROD_INPUT_PATH = os.path.join(ROOT_DIR, "data", "candidates.jsonl")
PROD_OUTPUT_PATH = os.path.join(ROOT_DIR, "submission.csv")
SAMPLE_OUTPUT_PATH = os.path.join(ROOT_DIR, "sample_testing_submission.csv")


def run_ranking_pipeline(script_path, input_file, output_file, top_n=100):
    try:
        cmd = [
            sys.executable, script_path, 
            "--candidates", input_file, 
            "--out", output_file, 
            "--top-n", str(top_n)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, cwd=ROOT_DIR)
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, f"Pipeline Error:\n{e.stderr}\n\nOutput Logs:\n{e.stdout}"
    except Exception as e:
        return False, str(e)

col_prod, col_sample = st.columns(2, gap="large")
with col_prod:
    
    
    if os.path.exists(PROD_INPUT_PATH):
        
        if st.button("Run Full Production Pipeline", use_container_width=True):
            with st.spinner("Processing full candidate set..."):
                success, logs = run_ranking_pipeline(RANK_SCRIPT_PATH, PROD_INPUT_PATH, PROD_OUTPUT_PATH)
            if success:
                st.success("Production Leaderboard compiled!")
            else:
                st.error("Production pipeline run failed.")
                st.code(logs)
    else:
        st.error("❌ Base `data/candidates.jsonl` file not found.")

    st.write("---")

    if os.path.exists(PROD_OUTPUT_PATH):
        try:
            df_prod = pd.read_csv(PROD_OUTPUT_PATH)
            st.dataframe(
                df_prod,
                use_container_width=True,
                column_config={
                    "rank": st.column_config.NumberColumn("Rank #", format="%d"),
                    "score": st.column_config.NumberColumn("Score", format="%.4f"),
                    "candidate_id": "Candidate ID",
                    "reasoning": "Match Analysis"
                },
                hide_index=True
            )
            
            with open(PROD_OUTPUT_PATH, "r", encoding="utf-8") as f:
                prod_bytes = f.read()
            st.download_button(
                label="Download Production Report (CSV)",
                data=prod_bytes,
                file_name=f"production_leaderboard_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error parsing production metrics: {e}")
    else:
        st.info("No active production run indexed yet.")

with col_sample:
    st.header("Sample Testing Sandbox")
  
    uploaded_sample = st.file_uploader(
        "Upload test snippet:", 
        type=["jsonl", "csv", "gz"],
        key="sample_sandbox"
    )
    
    if uploaded_sample is not None:
        file_ext = "." + uploaded_sample.name.split(".")[-1]
        temp_sample_input = os.path.join(ROOT_DIR, f"temp_sandbox_candidates{file_ext}")
        
        with open(temp_sample_input, "wb") as f:
            f.write(uploaded_sample.getbuffer())
            
        st.success(f"Staged `{uploaded_sample.name}` for test pass testing.")
        
        if st.button("Run Sandbox Validation", use_container_width=True):
            with st.spinner("Processing sample profile pass..."):
                success, logs = run_ranking_pipeline(RANK_SCRIPT_PATH, temp_sample_input, SAMPLE_OUTPUT_PATH, top_n=10)
            
            if os.path.exists(temp_sample_input):
                os.remove(temp_sample_input)
                
            if success:
                st.success("Sandbox test pass complete")
            else:
                st.error("Sandbox valuation processing failed.")
                st.code(logs)

    
    if os.path.exists(SAMPLE_OUTPUT_PATH):
        st.subheader("Sample Test Leaderboard")
        try:
            df_sample = pd.read_csv(SAMPLE_OUTPUT_PATH)
            st.dataframe(
                df_sample,
                use_container_width=True,
                column_config={
                    "rank": st.column_config.NumberColumn("Rank #", format="%d"),
                    "score": st.column_config.NumberColumn("Score", format="%.4f"),
                    "candidate_id": "Candidate ID",
                    "reasoning": "Match Analysis"
                },
                hide_index=True
            )
            
            with open(SAMPLE_OUTPUT_PATH, "r", encoding="utf-8") as f:
                sample_bytes = f.read()
            st.download_button(
                label=" Download Sandbox Report (CSV)",
                data=sample_bytes,
                file_name="sample_test_standings.csv",
                mime="text/csv",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Error parsing sample dataset results: {e}")
