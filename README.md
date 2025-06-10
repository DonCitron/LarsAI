# VQA (Visual Question Answering) Tool

A simple web application that analyzes multiple-choice questions from images using Anthropic's Claude 3 Opus model.

## Prerequisites

- Python 3.7+
- An Anthropic API key (from [console.anthropic.com](https://console.anthropic.com/))
- A device with a camera (for taking photos of questions)

## Setup

1. **Install required Python packages**:
   ```bash
   pip install Flask requests
   ```

2. **Set your Anthropic API key**:
   - On macOS/Linux:
     ```bash
     export ANTHROPIC_API_KEY='your-api-key-here'
     ```
   - On Windows (Command Prompt):
     ```batch
     set ANTHROPIC_API_KEY=your-api-key-here
     ```
   - On Windows (PowerShell):
     ```powershell
     $env:ANTHROPIC_API_KEY="your-api-key-here"
     ```

## Running the Application

1. Start the server:
   ```bash
   python app.py
   ```

2. The server will start and display a local IP address (e.g., `http://192.168.x.x:5000`).

3. On your mobile device (connected to the same WiFi network as your computer), open a web browser and navigate to the displayed IP address and port.

## Usage

1. Tap the "Take/Select Photo" button on the web page.
2. Take a photo of a multiple-choice question or select an existing photo from your device.
3. The app will analyze the image and display the most likely correct answer.

## Important Notes

- This tool is for educational purposes only.
- Using this tool for academic dishonesty is strictly discouraged.
- You are responsible for any API usage costs from Anthropic.
- The tool uses Claude 3 Opus model, which provides high-quality analysis of images.

## Troubleshooting

- If the app doesn't work, ensure:
  - Your device is connected to the same WiFi network as the computer running the server.
  - The server is running and accessible from your network.
  - You have a valid OpenAI API key set in your environment variables.
  - You have sufficient credits in your OpenAI account.
