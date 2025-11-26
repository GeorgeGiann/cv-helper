# Notebooks

## kaggle_submission.ipynb

⚠️ **Work In Progress - Not Required for Submission**

This Jupyter notebook is intended to demonstrate the CV-Enhancer system in a Kaggle notebook environment, but it is **not fully functional yet** and is **NOT required for the seminar submission**.

### Current Status

- ⚠️ **Not functional**: The notebook cells are incomplete and may not execute successfully
- 📝 **Documentation only**: Use as reference for understanding the system architecture
- ✅ **Command-line works**: Use `test_pipeline.py` for actual deployment

### For Kaggle Submission

Instead of using this notebook, deploy the system via command line:

1. **Upload source code as Kaggle dataset:**
   ```bash
   tar -czf cv-helper-source.tar.gz src/ data/ requirements.txt
   ```

2. **Create a Kaggle notebook and add your dataset**

3. **Extract and run:**
   ```python
   # Extract source code
   import tarfile
   with tarfile.open("/kaggle/input/cv-helper-source/cv-helper-source.tar.gz", "r:gz") as tar:
       tar.extractall("/kaggle/working")

   # Install dependencies
   !pip install -q -r /kaggle/working/requirements.txt

   # Configure environment
   import os
   os.environ["MODE"] = "kaggle"
   os.environ["USER_INTERACTION_MODE"] = "non-interactive"
   os.environ["LLM_PROVIDER"] = "gemini"  # or your choice
   os.environ["LLM_MODEL"] = "gemini-1.5-flash"

   # Run pipeline
   !cd /kaggle/working && python test_pipeline.py --cv your_cv.pdf --job job_ad.txt
   ```

### Why Command-Line?

- ✅ **Fully tested and working**
- ✅ **Easier to debug**
- ✅ **More flexible configuration**
- ✅ **Better for production deployment**

The notebook approach requires additional setup for:
- Proper module imports
- Path configuration
- Async execution in Jupyter
- Output persistence

### Future Plans

This notebook may be completed in future versions to provide:
- Interactive demonstration
- Step-by-step execution
- Visualization of agent communication
- Real-time progress tracking

---

**For now, use the command-line approach documented in the main README and `.env.kaggle` configuration.**
