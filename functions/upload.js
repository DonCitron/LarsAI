const { spawn } = require('child_process');
const { writeFile } = require('fs').promises;
const { tmpdir } = require('os');
const { join } = require('path');
const { v4: uuidv4 } = require('uuid');

// This function will be called by Netlify
// eslint-disable-next-line no-unused-vars
exports.handler = async (event, context) => {
  // Only allow POST requests
  if (event.httpMethod !== 'POST') {
    return {
      statusCode: 405,
      body: 'Method Not Allowed',
    };
  }

  try {
    // Parse the multipart form data
    const boundary = event.headers['content-type'].split('boundary=')[1];
    const body = Buffer.from(event.body, 'base64');
    const parts = body.toString().split(`--${boundary}`);
    
    let fileData = null;
    let fileName = '';
    
    // Extract file from form data
    for (const part of parts) {
      if (part.includes('Content-Disposition: form-data;') && part.includes('filename=')) {
        const match = part.match(/filename="([^"]+)"/);
        if (match) {
          fileName = match[1];
          const content = part.split('\r\n\r\n')[1];
          fileData = Buffer.from(content, 'binary');
          break;
        }
      }
    }
    
    if (!fileData) {
      return {
        statusCode: 400,
        body: JSON.stringify({ error: 'No file uploaded' }),
      };
    }
    
    // Save file to temporary directory
    const tempFilePath = join(tmpdir(), `${uuidv4()}-${fileName}`);
    await writeFile(tempFilePath, fileData);
    
    // Call Python script to process the image
    const pythonProcess = spawn('python', ['app.py', tempFilePath]);
    
    let result = '';
    let error = '';
    
    // Collect data from stdout and stderr
    pythonProcess.stdout.on('data', (data) => {
      result += data.toString();
    });
    
    pythonProcess.stderr.on('data', (data) => {
      error += data.toString();
    });
    
    // Wait for the process to exit
    await new Promise((resolve, reject) => {
      pythonProcess.on('close', (code) => {
        if (code !== 0) {
          reject(new Error(`Python script exited with code ${code}: ${error}`));
        } else {
          resolve();
        }
      });
    });
    
    // Parse the result
    let response;
    try {
      response = JSON.parse(result);
    } catch (e) {
      return {
        statusCode: 500,
        body: JSON.stringify({ error: 'Failed to parse response from Python script' }),
      };
    }
    
    return {
      statusCode: 200,
      body: JSON.stringify(response),
    };
    
  } catch (error) {
    console.error('Error processing request:', error);
    return {
      statusCode: 500,
      body: JSON.stringify({ error: 'Internal server error', details: error.message }),
    };
  }
};
