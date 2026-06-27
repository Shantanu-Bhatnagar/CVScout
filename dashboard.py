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
@keyframes aurora {
        0% { background-position: 0% 50%; }
        50% { background-position: 100% 50%; }
        100% { background-position: 0% 50%; }
    }
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@700&family=Inter:ital,wght@0,400;1,400&family=Syne:wght@700&family=Plus+Jakarta+Sans:ital,wght@0,500;1,500&family=Montserrat:wght@800&family=Space+Grotesk:ital,wght@0,400;1,400&display=swap');
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
    0%{
    background-position: 200% center;}
    100%(
    background-position: -200% center;})
</style>
""", unsafe_allow_html=True)
st.markdown("<h1 class='title'> HIREGRAD </h1>",unsafe_allow_html=True)
st.markdown(
    """
    <style>
    .sliding-text
    {
        font-family: 'Inter', sans-serif;
            font-size: 12px;
            font-weight: 600;
            color: #73C2BE;   
            background: rgba(188, 150, 230, 0.05);
            border: 1px solid rgba(188, 150, 230, 0.15);
            padding: 20px;
            border-radius: 12px;
            text-align: center;
            overflow: hidden; 
            white-space: nowrap;
            animation: slideIn 0.8s cubic-bezier(0.25, 1, 0.5, 1) forwards;
    }

        @keyframes slideIn {
            0% {
                transform: translateY(30px);
                opacity: 0;
            }
            100% {
                transform: translateY(0);
                opacity: 1;
            }
        }
    </style>
    
    <div class="sliding-text">Upload your CSV files to get started!</div>
    """, unsafe_allow_html=True
 )
