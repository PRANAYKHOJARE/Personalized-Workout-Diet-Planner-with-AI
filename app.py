# app.py
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import json
from fpdf import FPDF
import io
import matplotlib.pyplot as plt

# ---------------------------
# Helper Functions
# ---------------------------
st.set_page_config(page_title="AI Workout & Diet Planner", layout="wide")

GEMINI_ENV = st.secrets.get("GEMINI_API_KEY") if "GEMINI_API_KEY" in st.secrets else None

def estimate_calories(age, weight, height, gender, goal):
    if gender.lower() == "male":
        bmr = 10*weight + 6.25*height - 5*age + 5
    else:
        bmr = 10*weight + 6.25*height - 5*age - 161
    maintenance = bmr * 1.4
    if goal.lower() == "lose fat":
        return int(maintenance * 0.8)
    elif goal.lower() == "build muscle":
        return int(maintenance * 1.15)
    else:
        return int(maintenance)

def gemini_generate_plan(prompt, api_key=None):
    # Sample plan with meals including prep tips and time-saving
    days=[]
    for d in range(3):
        date=(datetime.now()+timedelta(days=d)).isoformat()
        days.append({
            "day_number":d+1,
            "date":date,
            "workout":[
                {"time":"7:00 AM","exercise":"Push-ups","sets_reps":"3x12","notes":"Bodyweight"},
                {"time":"7:30 AM","exercise":"Jogging","sets_reps":"20 min","notes":"Outdoor"}
            ],
            "diet":[
                {"meal_name":"Healthy Oatmeal Breakfast",
                 "meal":"Breakfast",
                 "menu":"Oatmeal with fruits",
                 "calories":350,"protein":12,"carbs":60,"fat":6,
                 "prep_tips":"Use instant oats for faster cooking.",
                 "time_saving":"Prepare overnight oats."},
                {"meal_name":"Grilled Chicken Salad Lunch",
                 "meal":"Lunch",
                 "menu":"Grilled chicken salad",
                 "calories":500,"protein":40,"carbs":35,"fat":20,
                 "prep_tips":"Grill chicken in bulk for multiple days.",
                 "time_saving":"Chop veggies in advance."},
                {"meal_name":"Veg Stir-Fry Dinner",
                 "meal":"Dinner",
                 "menu":"Vegetable stir-fry with rice",
                 "calories":450,"protein":15,"carbs":70,"fat":10,
                 "prep_tips":"Use pre-cut veggies from store.",
                 "time_saving":"Cook rice in pressure cooker."}
            ],
            "daily_total_calories":1300,
            "tips":"Stay hydrated and sleep 7+ hours."
        })
    total_calories=sum(day["daily_total_calories"] for day in days)
    return json.dumps({"days":days,"summary":"Sample AI-generated student fitness plan","total_calories":total_calories}, indent=2)

def create_pdf(plan):
    pdf=FPDF()
    pdf.add_page()
    pdf.set_font("Arial","B",16)
    pdf.cell(0,10,"AI Student Workout & Diet Plan",ln=True,align="C")
    pdf.ln(10)
    pdf.set_font("Arial","",12)
    pdf.cell(0,8,f"Summary: {plan.get('summary','')}",ln=True)
    pdf.cell(0,8,f"Total estimated calories: {plan.get('total_calories','N/A')}",ln=True)
    pdf.ln(5)
    for day in plan.get("days",[]):
        pdf.set_font("Arial","B",14)
        pdf.cell(0,8,f"Day {day['day_number']} ({day.get('date','')})",ln=True)
        pdf.set_font("Arial","B",12)
        pdf.cell(0,6,"Workout:",ln=True)
        pdf.set_font("Arial","",12)
        for w in day["workout"]:
            pdf.multi_cell(0,6,f"{w['time']} - {w['exercise']} ({w['sets_reps']}) [{w['notes']}]")
        pdf.set_font("Arial","B",12)
        pdf.cell(0,6,"Diet:",ln=True)
        pdf.set_font("Arial","",12)
        for m in day["diet"]:
            pdf.multi_cell(0,6,
                f"{m['meal_name']} ({m['meal']}): {m['menu']} (~{m['calories']} kcal, P:{m['protein']}g C:{m['carbs']}g F:{m['fat']}g)\n"
                f"Preparation Tips: {m.get('prep_tips','')}\n"
                f"Time-saving: {m.get('time_saving','')}"
            )
        pdf.cell(0,6,f"Daily tips: {day.get('tips','')}",ln=True)
        pdf.ln(5)
    buf=io.BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf

# ---------------------------
# Sidebar Inputs
# ---------------------------
st.sidebar.title("Settings & API Key")
gemini_key=st.sidebar.text_input("Gemini API key",type="password",value=GEMINI_ENV or "")
st.sidebar.markdown("Provide Gemini API key for AI plan. Fallback plan will be used otherwise.")

# ---------------------------
# Main Page
# ---------------------------
st.title("🏋️ AI Personalized Workout & Diet Planner")

st.header("Student Profile & Preferences")
c1,c2=st.columns(2)
with c1:
    age=st.number_input("Age (years)",10,100,20)
    weight=st.number_input("Weight (kg)",30,200,60)
    height=st.number_input("Height (cm)",100,250,170)
    gender=st.selectbox("Gender",["Male","Female"])
with c2:
    goal=st.selectbox("Fitness Goal",["Build muscle","Lose fat","Maintain fitness","Improve stamina"])
    diet_pref=st.multiselect("Dietary Preferences",["Vegetarian","Vegan","Non-Veg","Gluten-Free","Low-Carb"],default=["Vegetarian"])
    budget=st.number_input("Weekly food budget (INR)",500,10000,2000,step=100)
    duration_days=st.slider("Plan Duration (days)",1,14,3)

submitted=st.button("Generate Plan")

# ---------------------------
# Metrics
# ---------------------------
daily_calories=estimate_calories(age,weight,height,gender,goal)
st.metric("Estimated Daily Calories",f"{daily_calories} kcal")
st.metric("Plan Duration",f"{duration_days} days")
st.metric("Weekly Budget",f"₹{budget}")

# ---------------------------
# AI Prompt Preview
# ---------------------------
prompt_text=f"Create a {duration_days}-day personalized workout and diet plan for a student age {age}, gender {gender}, weight {weight}kg, height {height}cm, goal '{goal}', dietary preferences {diet_pref}, weekly budget INR {budget}, aiming {daily_calories} kcal/day. Output JSON with keys: days(list), summary, total_calories. Each day: workout(time,exercise,sets_reps,notes), diet(meal_name,meal,menu,calories,protein,carbs,fat,prep_tips,time_saving), tips."
st.subheader("💡 AI Prompt Preview")
st.text_area("Prompt",prompt_text,height=200)

# ---------------------------
# Generate Plan
# ---------------------------
if 'plan' not in st.session_state:
    st.session_state.plan = {}

if submitted:
    with st.spinner("Generating AI plan..."):
        try:
            if gemini_key:
                plan_text=gemini_generate_plan(prompt_text,api_key=gemini_key)
            else:
                st.warning("Using fallback plan.")
                plan_text=gemini_generate_plan(prompt_text)
        except Exception as e:
            st.error(f"AI API error: {e}")
            plan_text=gemini_generate_plan(prompt_text)
        st.session_state.plan=json.loads(plan_text)
    st.success("Plan generated!")

plan = st.session_state.plan

# ---------------------------
# Display Plan & Insights
# ---------------------------
if plan:
    tab1, tab2 = st.tabs(["Generated Plan", "Fitness & Exercise Insights"])

    # Tab 1: Generated Plan
    with tab1:
        st.header("Generated Workout & Diet Plan")
        for day in plan.get("days", []):
            with st.expander(f"Day {day['day_number']} ({day.get('date','')})"):
                st.subheader("🏋️ Workout")
                for w in day["workout"]:
                    st.write(f"- {w['time']} - {w['exercise']} ({w['sets_reps']}) [{w['notes']}]")
                st.subheader("🥗 Diet")
                for m in day["diet"]:
                    st.write(f"- {m.get('meal_name','')} ({m['meal']}): {m['menu']} (~{m['calories']} kcal, P:{m['protein']}g C:{m['carbs']}g F:{m['fat']}g)")
                    st.write(f"  Preparation Tips: {m.get('prep_tips','')}")
                    st.write(f"  Time-saving Suggestion: {m.get('time_saving','')}")
                st.write(f"Daily Tips: {day.get('tips','')}")

    # Tab 2: Fitness & Exercise Insights
    with tab2:
        st.header("💪 Fitness & Exercise Insights")
        for day in plan.get("days", []):
            st.subheader(f"Day {day['day_number']} ({day.get('date','')})")
            cardio = sum(1 for w in day["workout"] if "jog" in w["exercise"].lower() or "run" in w["exercise"].lower())
            strength = sum(1 for w in day["workout"] if "push" in w["exercise"].lower() or "squat" in w["exercise"].lower())
            st.write(f"Cardio Exercises: {cardio}, Strength Exercises: {strength}")
            labels = ["Cardio", "Strength"]
            sizes = [cardio, strength]
            fig, ax = plt.subplots()
            ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
            ax.set_title("Workout Type Distribution")
            st.pyplot(fig)
            total_burned = 0
            for w in day["workout"]:
                if "jog" in w["exercise"].lower() or "run" in w["exercise"].lower():
                    mins = int(w["sets_reps"].split()[0]) if "min" in w["sets_reps"] else 10
                    total_burned += mins * 8
                else:
                    reps_sets = w["sets_reps"].split('x')
                    if len(reps_sets) == 2:
                        total_burned += int(reps_sets[0]) * int(reps_sets[1]) * 0.5
            st.write(f"Estimated Calories Burned: {int(total_burned)} kcal")
            if strength > cardio:
                st.info("Focus on balancing cardio with strength exercises.")
            elif cardio > strength:
                st.info("Good cardio day! Consider adding some strength training.")
            if cardio > 0:
                st.success("Cardio included today – good for stamina!")
            if strength > 0:
                st.success("Strength exercises included – good for muscle building!")

# ---------------------------
# Export Options
# ---------------------------
st.header("📤 Export Your Plan")
if plan:
    export_format=st.selectbox("Export Format",["JSON","CSV","PDF","TXT"])

    if export_format=="JSON":
        st.download_button(
            "Download JSON",
            data=json.dumps(plan,indent=2,ensure_ascii=False),
            file_name="plan.json",
            mime="application/json"
        )

    elif export_format=="CSV":
        rows=[]
        for day in plan.get("days",[]):
            for w in day["workout"]:
                rows.append({
                    "day":day["day_number"],
                    "date":day.get("date",""),
                    "type":"Workout",
                    "time":w["time"],
                    "activity":w["exercise"],
                    "details":f"{w['sets_reps']} | {w['notes']}"
                })
            for m in day["diet"]:
                rows.append({
                    "day":day["day_number"],
                    "date":day.get("date",""),
                    "type":"Diet",
                    "meal_name": m.get("meal_name",""),
                    "meal": m["meal"],
                    "activity": m["menu"],
                    "calories": m["calories"],
                    "protein": m["protein"],
                    "carbs": m["carbs"],
                    "fat": m["fat"],
                    "prep_tips": m.get("prep_tips",""),
                    "time_saving": m.get("time_saving","")
                })
        df=pd.DataFrame(rows)
        st.download_button(
            "Download CSV",
            data=df.to_csv(index=False),
            file_name="plan.csv",
            mime="text/csv"
        )

    elif export_format=="PDF":
        pdf_buf=create_pdf(plan)
        st.download_button(
            "Download PDF",
            data=pdf_buf,
            file_name="plan.pdf",
            mime="application/pdf"
        )

    elif export_format=="TXT":
        txt_lines=[]
        txt_lines.append(plan.get("summary",""))
        for day in plan.get("days",[]):
            txt_lines.append(f"\nDay {day['day_number']} ({day.get('date','')})")
            txt_lines.append("Workout:")
            for w in day["workout"]:
                txt_lines.append(f"  - {w['time']} - {w['exercise']} ({w['sets_reps']}) [{w['notes']}]")
            txt_lines.append("Diet:")
            for m in day["diet"]:
                txt_lines.append(f"  - {m.get('meal_name','')} ({m['meal']}): {m['menu']} (~{m['calories']} kcal, P:{m['protein']}g C:{m['carbs']}g F:{m['fat']}g)")
                txt_lines.append(f"    Preparation Tips: {m.get('prep_tips','')}")
                txt_lines.append(f"    Time-saving Suggestion: {m.get('time_saving','')}")
            txt_lines.append(f"Tips: {day.get('tips','')}")
        st.download_button(
            "Download TXT",
            data="\n".join(txt_lines),
            file_name="plan.txt",
            mime="text/plain"
        )

st.success("Done! Adjust inputs to generate a new plan. 🏋️🥗")
