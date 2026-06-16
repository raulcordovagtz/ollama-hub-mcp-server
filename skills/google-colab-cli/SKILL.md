---
name: google-colab-cli
description: "Use the Google Colab CLI to offload heavy computational tasks (like fine-tuning, large-scale inference, or batch processing) to remote Colab runtimes with high-powered CPU, GPU, or TPU accelerators."
---

# Google Colab CLI (External Compute Skill)

This skill enables agents and developers to offload computational tasks to Google Colab's cloud resources (CPU, GPU, and TPU) directly from the local terminal.

## 🔐 Authentication & Account Management

The Google Colab CLI supports two authentication modes: **OAuth2** (default) and **Application Default Credentials (ADC)**.

### How to Select a Google Account

If you have multiple Google accounts, you can manage them in three ways:

#### Option A: Clear Cache & Re-authenticate (OAuth2)
By default, OAuth2 caches the active token in `~/.config/colab-cli/token.json`. To switch accounts:
1. Delete or rename the token:
   ```bash
   rm ~/.config/colab-cli/token.json
   ```
2. Run any `colab` command. The browser will open, allowing you to select and authorize the desired Google account.

#### Option B: Google Cloud SDK (ADC) - Recommended for Switching
If you have `gcloud` installed, you can switch accounts instantly using `gcloud configurations`:
1. Create a configuration for each account:
   ```bash
   gcloud config configurations create personal
   gcloud config configurations create work
   ```
2. Log in under each configuration with the required Colab scopes:
   ```bash
   gcloud auth application-default login \
     --scopes=openid,\
   https://www.googleapis.com/auth/cloud-platform,\
   https://www.googleapis.com/auth/userinfo.email,\
   https://www.googleapis.com/auth/colaboratory
   ```
3. Switch accounts anytime by running:
   ```bash
   gcloud config configurations activate work
   ```
4. Tell the CLI to use ADC:
   ```bash
   colab --auth=adc <command>
   ```

#### Option C: Session Isolation
To run multiple sessions under different accounts simultaneously, use the `--config` flag to specify separate configuration paths:
```bash
colab --config ~/.config/colab-cli/sessions_work.json --auth=oauth2 whoami
```

---

## 🚀 Basic Workflows

### 1. Provisioning Runtimes
Create a new remote session using the `colab new` command. Always provide a session name (`-s <name>`) for clarity.

*   **CPU Instance (Default):**
    ```bash
    colab new -s my-cpu-job
    ```
*   **GPU Instance (T4/L4/A100):**
    ```bash
    colab new -s my-gpu-job --gpu T4
    ```
*   **TPU Instance (v5e1/v6e1):**
    ```bash
    colab new -s my-tpu-job --tpu v6e1
    ```

### 2. Installing Packages
Install Python packages directly on the remote VM using:
```bash
colab install -s my-gpu-job transformers datasets peft trl bitsandbytes
```
You can also pass a requirements file:
```bash
colab install -s my-gpu-job -r requirements.txt
```

### 3. Remote Execution
Execute a local script or notebook file on the remote machine:
*   **Run local Python script:**
    ```bash
    colab exec -s my-gpu-job -f train.py
    ```
*   **Run Jupyter Notebook cell-by-cell:**
    ```bash
    colab exec -s my-gpu-job -f pipeline.ipynb
    ```
    *Creates `pipeline_output.ipynb` locally with the execution results.*

### 4. Interactive Console & REPL
For debugging, drop into an interactive Python shell or terminal session:
```bash
colab repl -s my-gpu-job
colab console -s my-gpu-job
```

### 5. File Operations & Download
Move files between your local system and the remote environment:
*   **Upload dataset:**
    ```bash
    colab upload -s my-gpu-job -l local_data.csv -r /content/data.csv
    ```
*   **Download model adapters:**
    ```bash
    colab download -s my-gpu-job -r /content/adapter_model.safetensors -l ./adapter_model.safetensors
    ```

### 6. Cleanup (Crucial to avoid charges)
Always terminate your session once finished:
```bash
colab stop -s my-gpu-job
```

---

## ⚡ Ephemeral One-Shot Jobs (`colab run`)

If you want to run a script end-to-end without managing the session lifecycle manually, use `colab run`. It provisions a VM, runs your script, and automatically terminates the VM.

```bash
colab run --gpu T4 -s one-shot-training train.py --epochs 3 --batch-size 16
```
Use the `--keep` flag if you want to keep the session alive after the script completes.
