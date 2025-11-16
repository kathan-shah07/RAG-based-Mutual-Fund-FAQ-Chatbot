// API endpoint - adjust if your backend runs on a different port
const API_BASE_URL = 'http://localhost:8000';
const API_ENDPOINT = `${API_BASE_URL}/api/v1/query`;

// Note: API call counter has been removed for cleaner UI

// Note: Number highlighting has been removed for cleaner display
// Numbers are still properly formatted by the LLM and displayed correctly

// Convert markdown to HTML
function markdownToHtml(text) {
    // First escape HTML to prevent XSS, but preserve markdown structure
    let escaped = escapeHtml(text);
    const lines = escaped.split('\n');
    const result = [];
    let inList = false;
    let i = 0;
    
    while (i < lines.length) {
        const line = lines[i];
        
        // Check for markdown table
        if (line.includes('|') && i + 1 < lines.length && lines[i + 1].match(/^\|[-:\s\|]+\|$/)) {
            // Found a table - process it
            const tableLines = [line];
            i++;
            // Skip separator line
            if (i < lines.length && lines[i].match(/^\|[-:\s\|]+\|$/)) {
                i++;
            }
            // Collect all table rows
            while (i < lines.length && lines[i].includes('|') && !lines[i].match(/^\|[-:\s\|]+\|$/)) {
                tableLines.push(lines[i]);
                i++;
            }
            
            // Build table HTML with proper structure
            if (tableLines.length > 0) {
                const headerCells = tableLines[0].split('|').filter(c => c.trim()).map(c => `<th>${c.trim()}</th>`).join('');
                const tableRows = tableLines.slice(1).map(row => {
                    const cells = row.split('|').filter(c => c.trim()).map(c => {
                        // Format table cells without highlighting
                        const cellContent = c.trim();
                        return `<td>${cellContent}</td>`;
                    }).join('');
                    return `<tr>${cells}</tr>`;
                }).join('');
                result.push(`<table class="formatted-table"><thead><tr>${headerCells}</tr></thead><tbody>${tableRows}</tbody></table>`);
            }
            continue;
        }
        
        // Check for markdown list item
        const listMatch = line.match(/^([\*\-\+])\s+(.+)$/);
        if (listMatch) {
            if (!inList) {
                result.push('<ul>');
                inList = true;
            }
            // Format list items without highlighting
            const listContent = listMatch[2];
            result.push(`<li>${listContent}</li>`);
        } else {
            if (inList) {
                result.push('</ul>');
                inList = false;
            }
            if (line.trim()) {
                // Format regular text lines without highlighting
                result.push(line);
            } else {
                result.push('<br>');
            }
        }
        i++;
    }
    
    // Close any open list
    if (inList) {
        result.push('</ul>');
    }
    
    // Join and convert remaining newlines to <br>, but preserve HTML structure
    let finalText = result.join('\n');
    // Convert newlines between text (not inside HTML tags) to <br>
    finalText = finalText.replace(/([^>\n])\n([^<\n])/g, '$1<br>$2');
    // Clean up multiple <br> tags
    finalText = finalText.replace(/(<br>\s*){2,}/g, '<br>');
    
    return finalText;
}

// Check if answer is a refusal message
function isRefusal(answer) {
    const refusalKeywords = [
        'cannot give investment advice',
        'cannot provide investment advice',
        'cannot give advice',
        'cannot provide advice',
        'only provide factual information',
        'no investment advice',
        'cannot recommend',
        'cannot suggest'
    ];
    
    const lowerAnswer = answer.toLowerCase();
    return refusalKeywords.some(keyword => lowerAnswer.includes(keyword));
}

// Normalize URL to ensure it's a full URL
function normalizeUrl(url) {
    if (!url || typeof url !== 'string') {
        return null;
    }
    
    url = url.trim();
    if (!url) {
        return null;
    }
    
    // Remove trailing punctuation
    url = url.replace(/[.,;:!?)\]]+$/, '');
    
    // If URL doesn't start with http:// or https://, try to add https://
    if (!url.match(/^https?:\/\//i)) {
        // Check if it looks like a domain
        if (url.match(/^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}/)) {
            url = 'https://' + url;
        } else {
            return null;
        }
    }
    
    // Validate URL structure
    try {
        const urlObj = new URL(url);
        return urlObj.href; // Return normalized full URL
    } catch (e) {
        return null;
    }
}

// Extract citation URLs from answer or sources (supports multiple citations)
function extractCitations(answer, sources, citationUrlsFromApi = null) {
    const citations = [];
    const seenUrls = new Set(); // Track normalized URLs to avoid duplicates
    
    // Helper function to add URL if valid and not duplicate
    function addUrl(url) {
        if (!url) return;
        const normalized = normalizeUrl(url);
        if (normalized && !seenUrls.has(normalized)) {
            citations.push(normalized);
            seenUrls.add(normalized);
        }
    }
    
    // First, use citation_urls from API response if available (most reliable)
    if (citationUrlsFromApi && Array.isArray(citationUrlsFromApi)) {
        for (const url of citationUrlsFromApi) {
            addUrl(url);
        }
    }
    
    // Always check sources metadata to ensure we have all unique URLs
    // This ensures we capture all sources even if citation_urls is incomplete
    if (sources && sources.length > 0) {
        for (const source of sources) {
            if (source.metadata && source.metadata.source_url) {
                addUrl(source.metadata.source_url);
            }
        }
    }
    
    // Also try to extract URLs from answer text (for multiple citations)
    // This catches any URLs the LLM might have included in the answer
    const urlRegex = /(?:Source\s*\d*:?\s*)?(https?:\/\/[^\s\)\]\>\"\'\n]+)/gi;
    const urlMatches = answer.matchAll(urlRegex);
    for (const match of urlMatches) {
        if (match[1]) {
            addUrl(match[1]);
        }
    }
    
    return citations;
}

// Display a message in the chat
function displayMessage(text, type = 'assistant', citationUrls = null, lastUpdated = null) {
    const chatMessages = document.getElementById('chat-messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}`;
    
    // Convert markdown to HTML for assistant messages (for lists and tables)
    let messageHTML;
    if (type === 'assistant') {
        // Process markdown formatting
        let processedText = markdownToHtml(text);
        messageHTML = `<div>${processedText}</div>`;
    } else {
        // For user messages and other types, just escape HTML
        messageHTML = `<div>${escapeHtml(text)}</div>`;
    }
    
    // Add "Last updated from sources" line for assistant messages
    if (type === 'assistant' && lastUpdated) {
        messageHTML += `<div class="last-updated">Last updated from sources: ${escapeHtml(lastUpdated)}</div>`;
    }
    
    // Add citations if available and not a refusal or error
    // Also check if the text itself is a refusal (to handle cases where citation might be extracted)
    if (citationUrls && type !== 'refusal' && type !== 'error' && !isRefusal(text)) {
        // Handle both single URL (string) and multiple URLs (array)
        const urls = Array.isArray(citationUrls) ? citationUrls : (citationUrls ? [citationUrls] : []);
        
        // Filter out any invalid URLs before displaying
        const validUrls = urls.filter(url => {
            const normalized = normalizeUrl(url);
            return normalized !== null && normalized !== undefined;
        }).map(url => normalizeUrl(url));
        
        // Show only the first (primary) citation
        if (validUrls.length > 0) {
            messageHTML += '<div class="citations">';
            // Single citation - ensure it's a full URL
            const fullUrl = validUrls[0];
            messageHTML += `
                <div class="citation">
                    <a href="${escapeHtml(fullUrl)}" target="_blank" rel="noopener noreferrer">
                        Source: ${escapeHtml(fullUrl)}
                    </a>
                </div>
            `;
            messageHTML += '</div>';
        }
    }
    
    messageDiv.innerHTML = messageHTML;
    chatMessages.appendChild(messageDiv);
    
    // Scroll to bottom
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Show loading message
function showLoading() {
    const chatMessages = document.getElementById('chat-messages');
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'loading-message';
    loadingDiv.className = 'message loading';
    loadingDiv.textContent = 'Thinking...';
    chatMessages.appendChild(loadingDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Remove loading message
function removeLoading() {
    const loadingMessage = document.getElementById('loading-message');
    if (loadingMessage) {
        loadingMessage.remove();
    }
}

// Validate for PII (Personally Identifiable Information)
function containsPII(text) {
    if (!text) return null;
    
    const lowerText = text.toLowerCase();
    
    // PAN card pattern: 5 letters, 4 digits, 1 letter (e.g., ABCDE1234F)
    const panPattern = /\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b/i;
    if (panPattern.test(text)) {
        return 'PAN card number';
    }
    
    // Aadhaar pattern: 12 digits, possibly with spaces or hyphens (e.g., 1234 5678 9012)
    const aadhaarPattern = /\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b/;
    if (aadhaarPattern.test(text)) {
        return 'Aadhaar number';
    }
    
    // Account number patterns: 9-18 digits (common bank account lengths)
    const accountPattern = /\b\d{9,18}\b/;
    // But exclude years, amounts, and other common numbers
    const accountKeywords = /(account|acc|a\/c|ac no|account number|account no)/i;
    if (accountPattern.test(text) && accountKeywords.test(text)) {
        return 'Account number';
    }
    
    // OTP pattern: 4-8 digit codes, often with "OTP" keyword
    const otpPattern = /\b(otp|one.?time.?password)[\s:]*\d{4,8}\b/i;
    if (otpPattern.test(text)) {
        return 'OTP';
    }
    
    // Email pattern
    const emailPattern = /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/;
    if (emailPattern.test(text)) {
        return 'Email address';
    }
    
    // Phone number patterns: Indian formats (10 digits, with or without country code)
    // Matches: +91-1234567890, 91-1234567890, 01234567890, 1234567890, etc.
    const phonePattern = /\b(\+?91[\s-]?)?[6-9]\d{9}\b/;
    if (phonePattern.test(text)) {
        // Exclude common non-phone numbers (years, amounts, etc.)
        const yearPattern = /\b(19|20)\d{2}\b/;
        const amountPattern = /₹|rs\.?|rupees?/i;
        if (!yearPattern.test(text) && !amountPattern.test(text)) {
            return 'Phone number';
        }
    }
    
    return null;
}

// Validate comparison questions
function isValidComparison(question) {
    if (!question) return { valid: true };
    
    const lowerQuestion = question.toLowerCase();
    
    // Check if it's a comparison question
    const comparisonKeywords = [
        'compare', 'comparison', 'vs', 'versus', 'better', 'best', 
        'which is better', 'which one is better', 'difference between',
        'differences', 'which should', 'should i choose', 'recommend'
    ];
    
    const isComparison = comparisonKeywords.some(keyword => lowerQuestion.includes(keyword));
    
    if (!isComparison) {
        return { valid: true };
    }
    
    // Check for disallowed comparison types
    const disallowedKeywords = [
        'performance', 'returns', 'return', 'roi', 'profit', 'loss',
        'gain', 'growth', 'appreciation', 'depreciation', 'yield',
        'better', 'best', 'worst', 'should i', 'recommend', 'advice',
        'suggest', 'opinion', 'which is better', 'which one is better'
    ];
    
    const hasDisallowed = disallowedKeywords.some(keyword => lowerQuestion.includes(keyword));
    
    if (hasDisallowed) {
        return {
            valid: false,
            reason: 'I can only compare mutual funds on factual parameters like expense ratio, lock-in period, benchmark, or portfolio mix. I cannot compare performance, returns, or provide recommendations on which fund is better.'
        };
    }
    
    // Check for allowed factual comparison parameters
    const allowedKeywords = [
        'expense ratio', 'lock-in', 'lock in', 'benchmark', 'portfolio mix',
        'fund category', 'fund type', 'risk level', 'minimum investment',
        'minimum sip', 'exit load', 'fund manager', 'fund house'
    ];
    
    const hasAllowed = allowedKeywords.some(keyword => lowerQuestion.includes(keyword));
    
    if (!hasAllowed) {
        return {
            valid: false,
            reason: 'I can only compare mutual funds on factual parameters like expense ratio, lock-in period, benchmark, or portfolio mix. Please specify which factual parameters you want to compare.'
        };
    }
    
    return { valid: true };
}

// Submit question to API
async function submitQuestion() {
    const input = document.getElementById('question-input');
    const submitBtn = document.getElementById('submit-btn');
    const question = input.value.trim();
    
    if (!question) {
        return;
    }
    
    // Validate for PII
    const piiType = containsPII(question);
    if (piiType) {
        displayMessage(
            `I cannot process questions containing personally identifiable information (PII) such as ${piiType}. For your privacy and security, please do not enter sensitive information like PAN numbers, Aadhaar numbers, account details, phone numbers, or email addresses. Please rephrase your question without any sensitive information.`,
            'error'
        );
        return;
    }
    
    // Validate comparison questions
    const comparisonValidation = isValidComparison(question);
    if (!comparisonValidation.valid) {
        displayMessage(comparisonValidation.reason, 'refusal');
        return;
    }
    
    // Disable input and button
    input.disabled = true;
    submitBtn.disabled = true;
    
    // Display user question (only after validation passes)
    displayMessage(question, 'user');
    
    // Clear input
    input.value = '';
    
    // Show loading
    showLoading();
    
    try {
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                k: 5,
                return_sources: true,
                return_scores: false,
                clear_history: false
            })
        });
        
        removeLoading();
        
        if (!response.ok) {
            // Try to get error message from response
            let errorMessage = `API error: ${response.status} ${response.statusText}`;
            try {
                const errorData = await response.json();
                if (errorData.detail) {
                    errorMessage = errorData.detail;
                }
            } catch (e) {
                // If JSON parsing fails, use default message
            }
            
            // Display error message
            if (response.status === 400) {
                // Validation errors (PII or comparison restrictions)
                displayMessage(errorMessage, 'refusal');
            } else {
                // Other errors
                displayMessage(
                    'Sorry, I encountered an error while processing your question. Please try again later.',
                    'error'
                );
            }
            return;
        }
        
        const data = await response.json();
        
        // Check if it's a refusal
        if (isRefusal(data.answer)) {
            // Display refusal message without citation
            displayMessage(
                data.answer || 'I can only provide factual information and cannot give investment advice or recommendations. Please ask about specific facts like expense ratios, lock-in periods, or fund details.',
                'refusal',
                null  // Explicitly no citation for refusals
            );
        } else {
            // Extract citation URLs - but only use the primary (first) citation
            // Use citation_urls from API response for proper traceback
            const citationUrls = extractCitations(
                data.answer, 
                data.sources, 
                data.citation_urls  // Use citation_urls from API for proper traceback
            );
            
            // Only show the first citation (primary source)
            const primaryCitation = citationUrls.length > 0 ? [citationUrls[0]] : null;
            
            // Display answer with single citation and last updated date
            displayMessage(data.answer, 'assistant', primaryCitation, data.last_updated);
        }
        
    } catch (error) {
        removeLoading();
        console.error('Error:', error);
        displayMessage(
            'Sorry, I encountered an error while processing your question. Please try again later.',
            'error'
        );
    } finally {
        // Re-enable input and button
        input.disabled = false;
        submitBtn.disabled = false;
        input.focus();
    }
}

// Handle example question click
function askQuestion(question) {
    const input = document.getElementById('question-input');
    input.value = question;
    submitQuestion();
}

// Handle Enter key press
function handleKeyPress(event) {
    if (event.key === 'Enter') {
        submitQuestion();
    }
}

// Scraper status polling
let statusPollInterval = null;

function updateScraperStatus(status) {
    const statusElement = document.getElementById('scraper-status');
    const statusMessage = statusElement.querySelector('.status-message');
    const statusSpinner = statusElement.querySelector('.status-spinner');
    const statusProgress = statusElement.querySelector('.status-progress');
    const progressFill = statusElement.querySelector('.progress-fill');
    const progressText = statusElement.querySelector('.progress-text');
    
    if (status.is_running) {
        statusElement.style.display = 'block';
        statusMessage.textContent = status.message || 'Processing...';
        
        // Show progress if URLs are being processed
        if (status.urls_total > 0) {
            const processed = status.urls_processed.length;
            const percentage = Math.round((processed / status.urls_total) * 100);
            statusProgress.style.display = 'block';
            progressFill.style.width = `${percentage}%`;
            progressText.textContent = `${processed}/${status.urls_total} URLs processed`;
        } else {
            statusProgress.style.display = 'none';
        }
        
        // Update spinner based on operation
        if (status.current_operation === 'scraping') {
            statusSpinner.className = 'status-spinner scraping';
        } else if (status.current_operation === 'ingestion') {
            statusSpinner.className = 'status-spinner ingesting';
        } else {
            statusSpinner.className = 'status-spinner';
        }
    } else {
        // Hide after a delay if completed
        if (status.progress === 'completed') {
            setTimeout(() => {
                statusElement.style.display = 'none';
            }, 3000);
        } else {
            statusElement.style.display = 'none';
        }
    }
}

async function pollScraperStatus() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/v1/scraper-status`);
        if (response.ok) {
            const status = await response.json();
            updateScraperStatus(status);
            
            // Stop polling if not running and no error
            if (!status.is_running && !status.error) {
                if (statusPollInterval) {
                    clearInterval(statusPollInterval);
                    statusPollInterval = null;
                }
            }
        }
    } catch (error) {
        console.error('Error polling scraper status:', error);
    }
}

// Start polling when page loads
document.addEventListener('DOMContentLoaded', function() {
    document.getElementById('question-input').focus();
    
    // Poll status every 2 seconds
    statusPollInterval = setInterval(pollScraperStatus, 2000);
    
    // Initial poll
    pollScraperStatus();
});

