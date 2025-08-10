// Global variables
let startTime;
let processingTimer;

// Initialize the application
document.addEventListener("DOMContentLoaded", function () {
  initializeEventListeners();
  setupQuestionManagement();
});

function initializeEventListeners() {
  const submitBtn = document.getElementById("submitBtn");
  const addQuestionBtn = document.getElementById("addQuestionBtn");

  submitBtn.addEventListener("click", handleSubmit);
  addQuestionBtn.addEventListener("click", addQuestion);

  // Handle Enter key in inputs
  document.addEventListener("keypress", function (e) {
    if (e.key === "Enter" && e.target.classList.contains("question-input")) {
      e.preventDefault();
      handleSubmit();
    }
  });
}

function setupQuestionManagement() {
  // Remove question functionality
  document.addEventListener("click", function (e) {
    if (e.target.closest(".remove-question-btn")) {
      const questionGroup = e.target.closest(".question-input-group");
      const container = document.getElementById("questionsContainer");

      // Don't remove if it's the only question
      if (container.children.length > 1) {
        questionGroup.remove();
      } else {
        showError("At least one question is required");
      }
    }
  });
}

function addQuestion() {
  const container = document.getElementById("questionsContainer");
  const newQuestionGroup = document.createElement("div");
  newQuestionGroup.className = "question-input-group mb-3";

  newQuestionGroup.innerHTML = `
        <div class="flex items-center space-x-2">
            <input type="text" class="question-input flex-1 p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                   placeholder="Enter your question...">
            <button type="button" class="remove-question-btn bg-red-500 text-white p-3 rounded-lg hover:bg-red-600 transition-colors">
                <i class="fas fa-trash"></i>
            </button>
        </div>
    `;

  container.appendChild(newQuestionGroup);

  // Focus on the new input
  const newInput = newQuestionGroup.querySelector(".question-input");
  newInput.focus();
}

function validateInputs() {
  const documentUrl = document.getElementById("documentUrl").value.trim();
  const authToken = document.getElementById("authToken").value.trim();
  const questionInputs = document.querySelectorAll(".question-input");

  if (!documentUrl) {
    throw new Error("Document URL is required");
  }

  if (!authToken) {
    throw new Error("Authentication token is required");
  }

  const questions = [];
  questionInputs.forEach((input) => {
    const question = input.value.trim();
    if (question) {
      questions.push(question);
    }
  });

  if (questions.length === 0) {
    throw new Error("At least one question is required");
  }

  // Basic URL validation
  try {
    new URL(documentUrl);
  } catch {
    throw new Error("Please enter a valid URL");
  }

  return {
    documentUrl,
    authToken,
    questions,
  };
}

async function handleSubmit() {
  try {
    // Hide previous results and errors
    hideAllSections();

    // Validate inputs
    const { documentUrl, authToken, questions } = validateInputs();

    // Show loading
    showLoading();

    // Start timer
    startProcessingTimer();

    // Make API call
    const response = await fetch("/hackrx/run", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify({
        documents: documentUrl,
        questions: questions,
      }),
    });

    // Stop timer
    stopProcessingTimer();

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`
      );
    }

    const data = await response.json();

    // Hide loading and show results
    hideLoading();
    showResults(questions, data.answers);
  } catch (error) {
    console.error("Error:", error);
    hideLoading();
    showError(error.message);
  }
}

function startProcessingTimer() {
  startTime = Date.now();
  const timeDisplay = document.getElementById("processingTime");

  processingTimer = setInterval(() => {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    timeDisplay.textContent = `Processing time: ${elapsed}s`;
  }, 1000);
}

function stopProcessingTimer() {
  if (processingTimer) {
    clearInterval(processingTimer);
    processingTimer = null;
  }
}

function showLoading() {
  const loadingSection = document.getElementById("loadingSection");
  loadingSection.classList.remove("hidden");

  // Disable submit button
  const submitBtn = document.getElementById("submitBtn");
  submitBtn.disabled = true;
  submitBtn.innerHTML =
    '<i class="fas fa-spinner fa-spin mr-2"></i>Processing...';
}

function hideLoading() {
  const loadingSection = document.getElementById("loadingSection");
  loadingSection.classList.add("hidden");

  // Re-enable submit button
  const submitBtn = document.getElementById("submitBtn");
  submitBtn.disabled = false;
  submitBtn.innerHTML = '<i class="fas fa-search mr-2"></i>Analyze Document';

  stopProcessingTimer();
}

function showResults(questions, answers) {
  const resultsSection = document.getElementById("resultsSection");
  const resultsContainer = document.getElementById("resultsContainer");

  // Clear previous results
  resultsContainer.innerHTML = "";

  // Create result cards
  questions.forEach((question, index) => {
    const answer = answers[index] || "No answer provided";

    const resultCard = document.createElement("div");
    resultCard.className = "answer-card p-6 rounded-lg mb-6 question-item";

    resultCard.innerHTML = `
            <div class="mb-4">
                <h3 class="text-lg font-semibold text-gray-800 mb-2">
                    <i class="fas fa-question-circle mr-2 text-blue-500"></i>Question ${
                      index + 1
                    }
                </h3>
                <p class="text-gray-700 bg-blue-50 p-3 rounded-lg border-l-4 border-blue-400">${escapeHtml(
                  question
                )}</p>
            </div>
            <div>
                <h4 class="text-md font-semibold text-gray-800 mb-2">
                    <i class="fas fa-lightbulb mr-2 text-yellow-500"></i>Answer
                </h4>
                <div class="text-gray-700 p-4 bg-white rounded-lg border border-gray-200">
                    ${formatAnswer(answer)}
                </div>
            </div>
        `;

    resultsContainer.appendChild(resultCard);
  });

  // Show results section
  resultsSection.classList.remove("hidden");

  // Scroll to results
  resultsSection.scrollIntoView({ behavior: "smooth" });
}

function formatAnswer(answer) {
  // Basic formatting for better readability
  if (typeof answer !== "string") {
    return escapeHtml(String(answer));
  }

  // Handle multi-line answers
  return escapeHtml(answer).replace(/\n/g, "<br>");
}

function showError(message) {
  const errorSection = document.getElementById("errorSection");
  const errorMessage = document.getElementById("errorMessage");

  errorMessage.textContent = message;
  errorSection.classList.remove("hidden");

  // Scroll to error
  errorSection.scrollIntoView({ behavior: "smooth" });

  // Auto-hide after 10 seconds
  setTimeout(() => {
    errorSection.classList.add("hidden");
  }, 10000);
}

function hideAllSections() {
  document.getElementById("loadingSection").classList.add("hidden");
  document.getElementById("resultsSection").classList.add("hidden");
  document.getElementById("errorSection").classList.add("hidden");
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

// Utility functions for better UX
function copyToClipboard(text) {
  navigator.clipboard
    .writeText(text)
    .then(() => {
      // Could add a toast notification here
      console.log("Copied to clipboard");
    })
    .catch((err) => {
      console.error("Failed to copy: ", err);
    });
}

// Add keyboard shortcuts
document.addEventListener("keydown", function (e) {
  // Ctrl/Cmd + Enter to submit
  if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
    e.preventDefault();
    handleSubmit();
  }

  // Escape to clear errors
  if (e.key === "Escape") {
    hideAllSections();
  }
});

// Add auto-save functionality for form data
function saveFormData() {
  const formData = {
    documentUrl: document.getElementById("documentUrl").value,
    questions: Array.from(document.querySelectorAll(".question-input")).map(
      (input) => input.value
    ),
    // Don't save the token for security
  };

  localStorage.setItem("ragFormData", JSON.stringify(formData));
}

function loadFormData() {
  try {
    const savedData = localStorage.getItem("ragFormData");
    if (savedData) {
      const formData = JSON.parse(savedData);

      // Restore document URL
      if (formData.documentUrl) {
        document.getElementById("documentUrl").value = formData.documentUrl;
      }

      // Restore questions
      if (formData.questions && formData.questions.length > 0) {
        const container = document.getElementById("questionsContainer");
        container.innerHTML = ""; // Clear existing

        formData.questions.forEach((question) => {
          addQuestion();
          const inputs = container.querySelectorAll(".question-input");
          const lastInput = inputs[inputs.length - 1];
          lastInput.value = question;
        });
      }
    }
  } catch (error) {
    console.error("Failed to load saved form data:", error);
  }
}

// Auto-save on input changes
document.addEventListener("input", function (e) {
  if (e.target.matches("#documentUrl, .question-input")) {
    setTimeout(saveFormData, 500); // Debounce
  }
});

// Load saved data on page load
document.addEventListener("DOMContentLoaded", loadFormData);
