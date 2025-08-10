# RAG Document Query System - Frontend

A modern, responsive web interface for the RAG (Retrieval-Augmented Generation) document analysis system.

## Features

- **Clean, Modern UI**: Built with Tailwind CSS for a professional look
- **Responsive Design**: Works seamlessly on desktop and mobile devices
- **Multiple Questions**: Add and remove questions dynamically
- **Real-time Processing**: Shows processing time and loading states
- **Error Handling**: User-friendly error messages and validation
- **Auto-save**: Saves form data locally for convenience
- **Copy to Clipboard**: Easy copying of results
- **Keyboard Shortcuts**:
  - Ctrl/Cmd + Enter: Submit form
  - Escape: Clear errors

## How to Use

1. **Enter Document URL**: Provide the URL of the document you want to analyze (PDF, DOC, etc.)

2. **Add Questions**: Enter one or more questions about the document. You can:

   - Add new questions with the "Add Question" button
   - Remove questions with the trash icon
   - Press Enter in any question field to submit

3. **Authentication**: Enter your authentication token (required for API access)

4. **Submit**: Click "Analyze Document" or use Ctrl/Cmd + Enter

5. **View Results**: The system will process your request and display answers for each question

## Technical Details

### Files Structure

```
frontend/
├── index.html          # Main HTML file
├── script.js          # JavaScript functionality
├── styles.css         # Custom CSS styles
└── README.md          # This file
```

### Key Features in Code

- **Dynamic Question Management**: JavaScript handles adding/removing question inputs
- **Form Validation**: Client-side validation for required fields and URL format
- **Auto-save**: Uses localStorage to save form data
- **Responsive Design**: CSS Grid and Flexbox for mobile-friendly layout
- **Loading States**: Visual feedback during processing
- **Error Handling**: Comprehensive error display and handling

### API Integration

The frontend communicates with the FastAPI backend via:

- **Endpoint**: `POST /hackrx/run`
- **Authentication**: Bearer token in Authorization header
- **Request Format**:
  ```json
  {
    "documents": "https://example.com/document.pdf",
    "questions": ["Question 1", "Question 2"]
  }
  ```
- **Response Format**:
  ```json
  {
    "answers": ["Answer 1", "Answer 2"]
  }
  ```

## Customization

### Styling

- Main colors can be changed in `styles.css` CSS variables
- Tailwind classes can be modified in `index.html`
- Custom animations and effects are in `styles.css`

### Functionality

- Modify `script.js` to add new features
- Validation rules can be updated in the `validateInputs()` function
- API endpoint can be changed in the `handleSubmit()` function

## Browser Compatibility

- Modern browsers (Chrome 60+, Firefox 55+, Safari 12+)
- Responsive design for mobile devices
- Progressive enhancement for older browsers

## Development

To modify the frontend:

1. Edit the HTML, CSS, or JavaScript files
2. The FastAPI backend serves static files from the `frontend/` directory
3. Refresh the browser to see changes
4. No build process required - pure HTML/CSS/JS

## Security Notes

- Authentication tokens are not saved in localStorage for security
- Form data (except tokens) is auto-saved for user convenience
- All API calls use HTTPS when deployed properly
- Input validation prevents basic XSS attacks
