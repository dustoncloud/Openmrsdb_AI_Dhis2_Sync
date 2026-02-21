/* Bahmni AI Reporting Suite
 Copyright (c) 2026 [Deepak Neupane]
 *https://github.com/dustoncloud
 */ 
let currentReportData = null;
let currentReportName = "DailySummary";

// --- INITIALIZATION & LOG FETCHING ---

window.onload = () => {
    if (localStorage.getItem("bahmni_login") === "true") {
        document.getElementById("loginBox").style.display = "none";
        document.getElementById("app").style.display = "flex";
        showWelcome();
        loadSyncLogs();
    }
};

async function loadSyncLogs() {
    try {
        const response = await fetch('/ai/sync/logs');
        const logs = await response.json();

        const logBody = document.getElementById('log-body');
        const lastSyncText = document.getElementById('last-sync-text');
        
        if (logs && logs.length > 0) {
            const latest = logs[0];
            lastSyncText.innerHTML = `<i class="fas fa-check-circle" style="color: #48bb78"></i> 
                Last Sync: <b>${latest.timestamp}</b> | Period: <b>${latest.period}</b> | <b>${latest.count} Records</b>`;

            logBody.innerHTML = logs.map(log => `
                <tr>
                    <td>${log.timestamp}</td>
                    <td>${log.report}</td>
                    <td>${log.period}</td>
                    <td><span style="color:#63b3ed; font-weight:bold;">${log.count}</span></td>
                </tr>
            `).join('');
        }
    } catch (error) {
        console.error("Error fetching logs:", error);
    }
}

function toggleLogs() {
    const table = document.getElementById('sync-history-table');
    table.style.display = table.style.display === 'none' ? 'block' : 'none';
}

function showWelcome() {
    const msgArea = document.getElementById('messages');
    const welcomeHtml = `
        <div class="ai-msg" style="border-left: 4px solid #3182ce;">
            <strong>👋 Welcome to Database AI + Bahmni > DHIS2 Integration Assistant</strong>
            <p style="font-size: 13px; margin-top: 5px; color: #cbd5e0;">
                I can help you query medical records and sync them to DHIS2. 
                <br><br>
                <strong>Pro-tip:</strong> When a report is generated, I'll automatically check when that specific data was last synced!
            </p>
        </div>`;
    msgArea.innerHTML = welcomeHtml;
}

// LOGIN FUNCTION
function login() {
    const pwdInput = document.getElementById("pwd");
    const pwd = pwdInput.value.trim();
    
    if (pwd === "Admin123") { 
        localStorage.setItem("bahmni_login", "true"); 
        document.getElementById("loginBox").style.display = "none";
        document.getElementById("app").style.display = "flex";
        showWelcome();
        loadSyncLogs(); 
    } else { 
        alert("Invalid Password"); 
    }
}

function logout() { 
    localStorage.removeItem("bahmni_login");
    location.reload(); 
}

function newChat() { 
    document.getElementById("messages").innerHTML = ""; 
    currentReportData = null; 
    currentReportName = "DailySummary";
    showWelcome(); 
}

// --- CORE UTILITIES ---

function preset(q) { 
    document.getElementById("input").value = q; 
    sendMessage(); 
}

function toggleSyncPanel(checkbox) {
    const msgContainer = checkbox.closest('.ai-msg');
    const syncWorkflow = msgContainer.querySelector('.sync-workflow-container');
    const userIn = msgContainer.querySelector('.dhis-user');

    if (checkbox.checked) {
        syncWorkflow.style.display = "block";
        const savedUser = localStorage.getItem('dhis_last_user');
        if (savedUser) userIn.value = savedUser;
    } else {
        syncWorkflow.style.display = "none";
    }
}

function downloadCSV() {
    if (!currentReportData || currentReportData.length === 0) return;
    const keys = Object.keys(currentReportData[0]);
    const csvContent = [keys.join(','), ...currentReportData.map(row => keys.map(k => row[k]).join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `report_${new Date().getTime()}.csv`;
    a.click();
}

// UPDATED: LEARNING SUGGESTION UTILITY
async function suggestForLearning(btn, question, sql, reportName) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Checking...`;

    try {
        const response = await fetch('/ai/feedback/suggest', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                question: question,
                sql: sql,
                report_name: reportName
            })
        });
        const result = await response.json();
        
        if (result.status === "success" || result.status === "exists") {
            // Apply the "Already Trained/In Review" look
            btn.style.background = "#2d3748";
            btn.style.color = result.status === "exists" ? "#63b3ed" : "#48bb78";
            btn.style.cursor = "default";
            btn.innerHTML = result.status === "exists" 
                ? `<i class="fas fa-info-circle"></i> ${result.message}` 
                : `<i class="fas fa-check-circle"></i> Submitted`;
            btn.onclick = null;
        } else {
            alert("Error: " + result.message);
            btn.disabled = false;
            btn.innerHTML = `⭐ Train AI`;
        }
    } catch (e) {
        btn.disabled = false;
        btn.innerHTML = `⭐ Train AI`;
    }
}

// --- COMMUNICATION ---

async function sendMessage() {
    const input = document.getElementById('input');
    const msgArea = document.getElementById('messages');
    
    const startDate = document.getElementById('date-from').value;
    const endDate = document.getElementById('date-to').value;
    
    const question = input.value;
    if (!question.trim()) return;

    msgArea.innerHTML += `<div class="user-msg">${question} <br><small style="opacity:0.6; font-size:10px;">Range: ${startDate} to ${endDate}</small></div>`;
    input.value = '';

    try {
        const response = await fetch('/ai/query', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                question: question,
                start_date: startDate,
                end_date: endDate 
            })
        });
        const result = await response.json();
        currentReportData = result.data;
        currentReportName = result.report_name;

        // Sync Status Badge
        let syncStatusBadge = "";
        if (result.last_sync) {
            syncStatusBadge = `
                <div style="font-size: 11px; color: #48bb78; background: #1a202c; padding: 4px 8px; border-radius: 4px; border: 1px solid #2d3748;">
                    <i class="fas fa-history"></i> Last Synced: ${result.last_sync.timestamp} (${result.last_sync.period})
                </div>`;
        } else {
            syncStatusBadge = `
                <div style="font-size: 11px; color: #718096; background: #1a202c; padding: 4px 8px; border-radius: 4px; border: 1px solid #2d3748;">
                    <i class="fas fa-info-circle"></i> Not yet synced
                </div>`;
        }

        let tableHtml = `<table style="width:100%; border-collapse: collapse; margin-top:10px; font-size:13px; color: white; background-color: #2c2c2c; border: 1px solid #444;">`;
        if (currentReportData && currentReportData.length > 0 && !currentReportData[0].Error) {
            const headers = Object.keys(currentReportData[0]);
            tableHtml += `<thead><tr style="background-color: #444;">${headers.map(h => `<th style="padding:10px; border:1px solid #555; text-align:left;">${h}</th>`).join('')}</tr></thead><tbody>`;
            tableHtml += currentReportData.map((row, i) => `<tr style="background-color: ${i%2===0?'#333':'#3d3d3d'};">${headers.map(h => `<td style="padding:10px; border:1px solid #555;">${row[h]}</td>`).join('')}</tr>`).join('');
            tableHtml += '</tbody>';
        } else if (currentReportData && currentReportData[0] && currentReportData[0].Error) {
            tableHtml = `<div style="color:#f56565; padding:10px;">Error: ${currentReportData[0].Error}</div>`;
        }
        tableHtml += '</table>';

        const yearOptions = [2025, 2026, 2027, 2028, 2029, 2030].map(y => `<option value="${y}" ${y===2026?'selected':''}>${y}</option>`).join('');
        const monthOptions = [
            {v:"01", n:"Jan"}, {v:"02", n:"Feb"}, {v:"03", n:"Mar"}, {v:"04", n:"Apr"},
            {v:"05", n:"May"}, {v:"06", n:"Jun"}, {v:"07", n:"Jul"}, {v:"08", n:"Aug"},
            {v:"09", n:"Sep"}, {v:"10", n:"Oct"}, {v:"11", n:"Nov"}, {v:"12", n:"Dec"}
        ].map(m => `<option value="${m.v}">${m.n}</option>`).join('');

        // Clean strings for safely injecting into onclick attributes
        const safeQ = question.replace(/`/g, '\\`').replace(/'/g, "\\'");
        const safeSQL = result.sql.replace(/`/g, '\\`').replace(/'/g, "\\'");

        let aiHtml = `
            <div class="ai-msg">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                    <strong style="color: #63b3ed;">Analysis Result (${currentReportName})</strong>
                    ${syncStatusBadge}
                </div>
                <pre style="font-size:11px; background:#1e1e1e; color:#ddd; padding:8px; border-radius:4px; border:1px solid #333; white-space: pre-wrap;">${result.sql}</pre>
                <div style="overflow-x:auto;">${tableHtml}</div>
                
                <div style="margin-top:12px; display:flex; align-items:center; justify-content: space-between; gap:10px; background:#1a202c; padding:10px; border-radius:6px; border: 1px solid #333;">
                    <div style="display:flex; gap:8px;">
                        <button onclick="downloadCSV()" style="background:#4a5568; color:white; border:none; padding:8px 14px; border-radius:4px; cursor:pointer; font-size:12px; font-weight:bold;">📥 CSV</button>
                        
                        <button onclick="suggestForLearning(this, \`${safeQ}\`, \`${safeSQL}\`, '${currentReportName}')" 
                                style="background:#805ad5; color:white; border:none; padding:8px 14px; border-radius:4px; cursor:pointer; font-size:12px; font-weight:bold;">
                            ⭐ Train AI
                        </button>
                    </div>

                    <label style="color:#a0aec0; font-size:12px; cursor:pointer; display: flex; align-items: center; gap: 8px;">
                        <input type="checkbox" onchange="toggleSyncPanel(this)" class="sync-toggle-check" style="cursor:pointer; width:15px; height:15px;"> 
                        Sync to DHIS2?
                    </label>
                </div>

                <div class="sync-workflow-container" style="display:none; margin-top:10px;">
                    <div class="period-config" style="background:#2d3748; padding:15px; border-radius:8px 8px 0 0; border: 1px solid #4a5568; border-bottom: none;">
                        <p style="color:#63b3ed; font-size:11px; font-weight:bold; margin-bottom:10px; text-transform: uppercase;">📅 Step 1: Set Target Period</p>
                        <div style="display:flex; gap:10px;">
                            <div style="flex:1;"><label style="color:#cbd5e0; font-size:10px;">Year</label><select class="sync-year" style="width:100%; padding:8px; border-radius:4px; border:none; background:#1a202c; color:white; font-size:12px;">${yearOptions}</select></div>
                            <div style="flex:1;"><label style="color:#cbd5e0; font-size:10px;">Month</label><select class="sync-month" style="width:100%; padding:8px; border-radius:4px; border:none; background:#1a202c; color:white; font-size:12px;">${monthOptions}</select></div>
                        </div>
                    </div>
                    <div class="auth-sync-box" style="padding:15px; background:#2d3748; border:1px solid #4a5568; border-radius:0 0 8px 8px;">
                        <p style="color:#63b3ed; font-size:11px; font-weight:bold; margin-bottom:10px; text-transform: uppercase;">🔐 Step 2: DHIS2 Credentials</p>
                        <input type="text" class="dhis-user" placeholder="DHIS2 Username" style="width:100%; padding:8px; margin-bottom:8px; border-radius:4px; border:none; background:#1a202c; color:white; font-size:13px;">
                        <input type="password" class="dhis-pass" placeholder="DHIS2 Password" style="width:100%; padding:8px; margin-bottom:12px; border-radius:4px; border:none; background:#1a202c; color:white; font-size:13px;">
                        <button onclick="triggerDHIS2Sync(this)" style="background:#3182ce; color:white; border:none; padding:12px; border-radius:4px; cursor:pointer; font-weight:bold; width:100%; font-size:13px;">🚀 Push to DHIS2</button>
                        <div class="sync-status" style="font-size:12px; margin-top:10px; text-align:center;"></div>
                    </div>
                </div>
            </div>`;
        
        msgArea.innerHTML += aiHtml;
        msgArea.scrollTop = msgArea.scrollHeight;
    } catch (e) { 
        console.error(e);
        msgArea.innerHTML += `<div class="ai-msg" style="color:red">Error generating response.</div>`; 
    }
}

// --- DHIS2 SYNC ENGINE ---

async function triggerDHIS2Sync(btn) {
    const msgContainer = btn.closest('.ai-msg');
    const statusDiv = msgContainer.querySelector('.sync-status');
    const userIn = msgContainer.querySelector('.dhis-user');
    const passIn = msgContainer.querySelector('.dhis-pass');
    const yearVal = msgContainer.querySelector('.sync-year').value;
    const monthVal = msgContainer.querySelector('.sync-month').value;
    const periodStr = `${yearVal}${monthVal}`; 
    
    if (!userIn.value || !passIn.value) {
        statusDiv.style.color = "#f56565";
        statusDiv.innerHTML = "Credentials required.";
        return;
    }

    localStorage.setItem('dhis_last_user', userIn.value);
    btn.disabled = true;
    btn.innerText = "⌛ Synchronizing Data...";

    try {
        const response = await fetch('/ai/sync/dhis2', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ 
                data: currentReportData,
                report_name: currentReportName,
                period: periodStr, 
                dhis_user: userIn.value,
                dhis_pass: passIn.value
            })
        });

        const res = await response.json();

        if (res.status === "completed") {
            statusDiv.style.color = "#48bb78";
            statusDiv.innerHTML = `✅ ${res.message}`;
            btn.innerText = "Success ✓";
            loadSyncLogs(); 

            userIn.disabled = true;
            passIn.disabled = true;
            btn.style.background = "#2d3748";
        } else {
            statusDiv.style.color = "#f56565";
            statusDiv.innerHTML = `❌ ${res.message}`;
            btn.disabled = false;
            btn.innerText = "🚀 Push to DHIS2";
        }
    } catch (error) {
        statusDiv.innerHTML = `❌ Server Connection Error`;
        btn.disabled = false;
        btn.innerText = "🚀 Push to DHIS2";
    }
}