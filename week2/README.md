# AI Component

## Objective

## Project Setup

### Part 1: Ollama Setup

#### Step 1: Install Ollama

Go to [ollama.com](https://ollama.com/) and download the installer for your OS, or use the terminal:

macOS / Linux (one-liner):

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

macos (Homebrew):

```bash
brew install ollama
```

windows:

```bash
irm https://ollama.com/install.ps1 | iex
```

The direct download link for the v0.21.0 Windows installer is:

```
https://github.com/ollama/ollama/releases/download/v0.21.0/OllamaSetup.exe
```

Paste that URL directly into your browser to download it. This bypasses the GitHub releases page which defaults to the latest version.

#### Step 2: Verify the version is 0.21.x

After installation, check the version:

```bash
ollama -v
# Expected: ollama version is 0.21.0
```

If you need a specific version (0.21.0), on macOS you can pin it via Homebrew:

```bash
brew install ollama@0.21.0
```

#### Step 3: Start the Ollama server

```bash
ollama serve
```

Leave this running in a terminal tab, or on macOS you can run Ollama as a background app from the menu bar.

#### Step 4: Verify the server is running

In a new terminal:

```bash
curl 127.0.0.1:11434
# Expected response: Ollama is running
```

#### Step 5: Pull the three models 

Run each command (they download sequentially — sizes shown for reference):

```bash
ollama pull llama3.1        # ~4.9 GB
ollama pull phi3            # ~2.2 GB
ollama pull deepseek-r1:1.5b  # ~1.1 GB
```

These may take a while depending on your internet speed (~8 GB total).

#### Step 6: Verify all models are installed

```bash
ollama ls
```

You should see output like:

```
NAME                ID              SIZE      MODIFIED
deepseek-r1:1.5b    e0979632db5a    1.1 GB    About a minute ago
phi3:latest         4f2222927938    2.2 GB    2 minutes ago
llama3.1:latest     46e0c10c039e    4.9 GB    3 hours ago
```

### Part 2: Google AI Setup

#### Step 1: Get your API Key

1. Go to [aistudio.google.com](https://aistudio.google.com/)
2. Sign in with your Google account
3. Click "Get API Key" (top left or via the menu)
4. Click "Create API key" → copy and save it somewhere safe

#### Step 2: Find the Rate Limits

1. In AI Studio, click on "Get API Key" again
2. You'll see a table listing your keys — look for a "Rate limits" column or link
3. Alternatively, go to: [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) and click on "View rate limits" next to your key

For each model, look for these three columns:

RPM — Requests Per Minute
TPM — Tokens Per Minute
RPD — Requests Per Day

#### Step 3: Create the file

Once you have the numbers, create rate_limits.txt like this:

```bash
cat > rate_limits.txt << 'EOF'
gemini-2.5-flash <RPM> <TPM> <RPD>
gemini-2.5-flash-lite <RPM> <TPM> <RPD>
gemini-3-flash-preview <RPM> <TPM> <RPD>
EOF
```

Replace <RPM>, <TPM>, <RPD> with the actual numbers from your dashboard.

### Notes

Create `.env` file to store the secret configuration such as api key. `load_dotenv` from `dotenv` package needed.