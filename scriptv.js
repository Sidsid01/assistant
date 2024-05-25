
// Parse the response from your Python backend
const data = await response.json();

// Assuming your Python backend returns the user's input and the AI's response as JSON
const userInput = data.userInput;
const aiResponse = data.aiResponse;