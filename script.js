// script.js

document.addEventListener("DOMContentLoaded", function () {
    const userInput = document.getElementById("user-input");
    const submitBtn = document.getElementById("submit-btn");
    const aiOutput = document.getElementById("ai-output");

    submitBtn.addEventListener("click", async function () {
        const inputText = userInput.value.trim();
        if (inputText === "") {
            alert("Please enter your thoughts.");
            return;
        }

        // Send input text to the backend for analysis
        const response = await fetch("/analyze_emotion", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ text: inputText })
        });

        if (response.ok) {
            const data = await response.json();
            aiOutput.textContent = `AI Analysis: ${data.emotion}`;
        } else {
            aiOutput.textContent = "Error occurred during analysis.";
        }
    });
});

