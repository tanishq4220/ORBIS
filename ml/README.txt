ORBIS UNIT 4 — ML MODEL

1) From the ORBIS root folder:
   python ml/train_model.py

2) Then run the ACI pipeline:
   cd ACI
   python run.py

The model outputs Model_Confidence in [0,1] and ML_Prediction.

IMPORTANT: this emergency/demo version uses bootstrap labels derived from data-age and trajectory stability because the current project package does not contain enough independent historical SGP4/reference labels. For the final scientific version, replace the bootstrap labels in train_model.py with measured historical SGP4-vs-reference errors.
