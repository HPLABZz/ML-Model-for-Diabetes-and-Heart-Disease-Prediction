import pandas as pd
import joblib
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

dataset = pd.read_csv("dataset/biomedical heart and diabetes dataset.csv")
X = dataset.drop(["heart_disease","diabetes_risk","patient_id"], axis=1)
y_heart = dataset["heart_disease"]
y_diabetes = dataset["diabetes_risk"]

X_train, X_test, y_train_heart, y_test_heart = train_test_split(
    X, y_heart, test_size=0.2, random_state=42
)
X_train2, X_test2, y_train_diabetes, y_test_diabetes = train_test_split(
    X, y_diabetes, test_size=0.2, random_state=42
)
heart_model = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    random_state=42
)
diabetes_model = RandomForestClassifier(
    n_estimators=200,
    max_depth=10,
    random_state=42
)

heart_model.fit(X_train, y_train_heart)
diabetes_model.fit(X_train2, y_train_diabetes)
joblib.dump(heart_model, "models/heart_model.pkl")
joblib.dump(diabetes_model, "models/diabetes_model.pkl")
print("Models saved successfully.")

heart_pred = heart_model.predict(X_test)
diabetes_pred = diabetes_model.predict(X_test2)
heart_accuracy = accuracy_score(y_test_heart, heart_pred)
diabetes_accuracy = accuracy_score(y_test_diabetes, diabetes_pred)

print("MODEL ACCURACY")
print(f"For heart disease: {heart_accuracy*100:.2f}%")
print(f"For diabetes disease: {diabetes_accuracy*100:.2f}%")

feature_count = X.shape[1]
print(f"Enter Patient Data ({feature_count + 1} comma separated values required including patient_id):")
user_input = input()
values = [float(x) for x in user_input.split(",")]
patient_id = values[0]
features = values[1:]

input_data = pd.DataFrame([features], columns=X.columns)
heart_prob = heart_model.predict_proba(input_data)[0][1] * 100
diabetes_prob = diabetes_model.predict_proba(input_data)[0][1] * 100

print(f"\nPREDICTION RESULT\nHeart Disease Risk: {round(heart_prob,2)}%\nDiabetes Disease Risk: {round(diabetes_prob,2)}%")
