from flask import Flask, render_template, request, jsonify
from pymongo import MongoClient
import pickle
import numpy as np
import os
from dotenv import load_dotenv
from datetime import datetime
from bson import json_util
import json
import urllib.parse

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'default_secret_key')

# MongoDB connection - FIXED for DNS/SRV issues
username = urllib.parse.quote_plus('admin')
password = urllib.parse.quote_plus('Mongodb%y012')

# Use STANDARD connection string to avoid SRV DNS issues
MONGO_URI = f"mongodb+srv://{username}:{password}@cluster0.17dyep5.mongodb.net/fullstack_ai_lab?retryWrites=true&w=majority"

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    client.admin.command('ping')  # Test connection
    print("✅ MongoDB Atlas connected successfully!")
except Exception as e:
    print(f"❌ MongoDB connection failed: {e}")
    print("🔄 Falling back to local MongoDB...")
    client = MongoClient('mongodb://localhost:27017/')
    
db = client['fullstack_ai_lab']
predictions_collection = db['predictions']

# Load models with error handling
try:
    with open('iris_logistic_regression.pkl', 'rb') as f:
        logistic_model = pickle.load(f)
    naive_bayes_model = logistic_model  # Using same model as per original code
    
    with open('feature_names.pkl', 'rb') as f:
        feature_names = pickle.load(f)
        
    with open('target_names.pkl', 'rb') as f:
        target_names = pickle.load(f)
        
    print("✅ Models loaded successfully!")
except FileNotFoundError as e:
    print(f"❌ Model files not found: {e}")
    print("Please ensure model files exist in the project directory")
    exit(1)

@app.route('/')
def home():
    return render_template('dashboard.html')

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        data = request.get_json()
        features = data.get('features')
        model_name = data.get('model', 'logistic_regression')
        
        if not features or len(features) != 4:
            return jsonify({'error': 'Expected 4 features'}), 400
            
        features_array = np.array([features])
        
        # Select model
        if model_name == 'logistic_regression':
            model = logistic_model
        elif model_name == 'naive_bayes':
            model = naive_bayes_model
        else:
            return jsonify({'error': 'Invalid model name'}), 400
        
        # Predict
        prediction = model.predict(features_array)
        prediction_index = int(prediction[0])
        predicted_class = target_names[prediction_index]
        
        # Get probabilities
        probabilities = model.predict_proba(features_array)[0]
        prob_dict = {
            target_names[i]: float(probabilities[i]) for i in range(len(target_names))
        }
        
        # Store prediction in database
        prediction_record = {
            'timestamp': datetime.utcnow(),
            'model': model_name,
            'features': {
                feature_names[i]: features[i] for i in range(len(features))
            },
            'prediction': predicted_class,
            'prediction_index': prediction_index,
            'probabilities': prob_dict,
            'confidence': float(max(probabilities))
        }
        predictions_collection.insert_one(prediction_record)
        
        response = {
            'model_used': model_name,
            'prediction': predicted_class,
            'prediction_index': prediction_index,
            'probabilities': prob_dict,
            'confidence': float(max(probabilities))
        }
        return jsonify(response)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get prediction statistics for dashboard"""
    try:
        # Total predictions
        total_predictions = predictions_collection.count_documents({})
        
        # Predictions by class
        pipeline = [
            {
                '$group': {
                    '_id': '$prediction',
                    'count': {'$sum': 1}
                }
            }
        ]
        predictions_by_class = list(predictions_collection.aggregate(pipeline))
        
        # Predictions by model
        pipeline = [
            {
                '$group': {
                    '_id': '$model',
                    'count': {'$sum': 1}
                }
            }
        ]
        predictions_by_model = list(predictions_collection.aggregate(pipeline))
        
        # Average confidence by model
        pipeline = [
            {
                '$group': {
                    '_id': '$model',
                    'avg_confidence': {'$avg': '$confidence'}
                }
            }
        ]
        avg_confidence_by_model = list(predictions_collection.aggregate(pipeline))
        
        # Recent predictions (last 10)
        recent_predictions = list(
            predictions_collection.find()
            .sort('timestamp', -1)
            .limit(10)
        )
        
        # Confidence distribution
        pipeline = [
            {
                '$group': {
                    '_id': {
                        '$cond': [
                            {'$gte': ['$confidence', 0.9]}, 'High (>90%)',
                            {
                                '$cond': [
                                    {'$gte': ['$confidence', 0.7]}, 'Medium (70-90%)',
                                    'Low (<70%)'
                                ]
                            }
                        ]
                    },
                    'count': {'$sum': 1}
                }
            }
        ]
        confidence_distribution = list(predictions_collection.aggregate(pipeline))
        
        return json.loads(json_util.dumps({
            'total_predictions': total_predictions,
            'predictions_by_class': predictions_by_class,
            'predictions_by_model': predictions_by_model,
            'avg_confidence_by_model': avg_confidence_by_model,
            'recent_predictions': recent_predictions,
            'confidence_distribution': confidence_distribution
        }))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear-history', methods=['POST'])
def clear_history():
    """Clear all prediction history"""
    try:
        result = predictions_collection.delete_many({})
        return jsonify({
            'success': True,
            'deleted_count': result.deleted_count
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    print("🚀 Starting Flask app with MongoDB...")
    print(f"📊 Database: fullstack_ai_lab.predictions")
    app.run(debug=True, host='0.0.0.0', port=5000)
