/* Bahmni AI Reporting Suite
 * Integrated Version: Original Logic + Enhanced History UI
 */ 

let currentReportData = null;
let currentReportName = "DailySummary";

// --- NEW HISTORY STATE ---
let allLogs = [];
let filteredLogs = [];
let currentPage = 1;
const logsPerPage = 10;

// --- INITIALIZATION & LOG FETCHING ---

window.onload = () => {
    if (localStorage.getItem("bahmni_login") === "true") {
        document.getElementById("loginBox").style.display = "none";
        document.getElementById("app").style.display = "flex";
        showWelcome();
        loadSyncLogs();
    }
};

// UPGRADED: Handles search and pagination for large log sets
async function loadSyncLogs() {
    try {
        const response = await fetch('/ai/sync/logs');
        allLogs = await response.json();
        filteredLogs = [...allLogs];

        const lastSyncText = document.getElementById('last-sync-text');
        
        if (allLogs && allLogs.length > 0) {
            const latest = allLogs[0];
            lastSyncText.innerHTML = `<i class="fas fa-check-circle" style="color: #48bb78"></i> 
                Last Sync: <b>${latest.timestamp}</b> | Period: <b>${latest.period}</b> | <b>${latest.count} Records</b>`;
            renderLogsTable();
        }
    } catch (error) {
        console.error("Error fetching logs:", error);
    }
}

function renderLogsTable() {
    const logBody = document.getElementById('log-body');
    if (!logBody) return;

    const start = (currentPage - 1) * logsPerPage;
    const paginatedItems = filteredLogs.slice(start, start + logsPerPage);

    logBody.innerHTML = paginatedItems.map(log => `
        <tr>
            <td>${log.timestamp}</td>
            <td><span style="background:#2d3748; padding:2px 6px; border-radius:4px; font-size:11px; color:#63b3ed; border:1px solid #4a5568;">${log.report}</span></td>
            <td>${log.period}</td>
            <td><span style="color:#63b3ed; font-weight:bold;">${log.count}</span></td>
        </tr>
    `).join('');

    renderPaginationControls();
}

function renderPaginationControls() {
    const totalPages = Math.ceil(filteredLogs.length / logsPerPage) || 1;
    const navContainer = document.getElementById('log-pagination');
    if (!navContainer) return;

    navContainer.innerHTML = `
        <div style="display:flex; justify-content: space-between; align-items: center; padding: 10px; background: #1a202c; border-top: 1px solid #2d3748; font-size: 11px;">
            <span style="color: #718096">Showing ${filteredLogs.length > 0 ? (currentPage-1)*logsPerPage + 1 : 0}-${Math.min(currentPage*logsPerPage, filteredLogs.length)} of ${filteredLogs.length}</span>
            <div style="display:flex; gap: 8px;">
                <button onclick="changePage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''} style="cursor:pointer; background:#2d3748; color:white; border:none; padding:4px 8px; border-radius:4px;">Prev</button>
                <button onclick="changePage(${currentPage + 1})" ${currentPage >= totalPages ? 'disabled' : ''} style="cursor:pointer; background:#2d3748; color:white; border:none; padding:4px 8px; border-radius:4px;">Next</button>
            </div>
        </div>`;
}

function changePage(p) { currentPage = p; renderLogsTable(); }

function filterLogs(query) {
    const q = query.toLowerCase();
    filteredLogs = allLogs.filter(log => 
        log.report.toLowerCase().includes(q) || log.period.includes(q)
    );
    currentPage = 1;
    renderLogsTable();
}

function toggleLogs() {
    const table = document.getElementById('sync-history-table');
    const isHidden = table.style.display === 'none' || table.style.display === '';
    
    if (isHidden) {
        table.style.display = 'block';
        // Add search bar if it doesn't exist
        if (!document.getElementById('log-search-input')) {
            table.insertAdjacentHTML('afterbegin', `
                <div style="padding: 10px; background: #2d3748; border-bottom: 1px solid #4a5568;">
                    <input id="log-search-input" type="text" onkeyup="filterLogs(this.value)" placeholder="🔍 Search history..." 
                    style="width:100%; padding:8px; border-radius:4px; border:none; background:#1a202c; color:white; font-size:12px;">
                </div>`);
        }
    } else {
        table.style.display = 'none';
    }
}

// --- ORIGINAL UTILITIES (RESTORED) ---

function showWelcome() {
    const msgArea = document.getElementById('messages');
    msgArea.innerHTML = `
        <div class="ai-msg" style="border-left: 4px solid #3182ce;">
            <strong>👋 Welcome to Database AI + Bahmni > DHIS2 Integration Assistant</strong>
            <p style="font-size: 13px; margin-top: 5px; color: #cbd5e0;">
                I can help you query medical records and sync them to DHIS2. 
                <br><br>
                <strong>Pro-tip:</strong> When a report is generated, I'll automatically check when that specific data was last synced!
            </p>
        </div>`;
}

function login() {
    const pwd = document.getElementById("pwd").value.trim();
    if (pwd === "Admin123") { 
        localStorage.setItem("bahmni_login", "true"); 
        location.reload(); 
    } else { alert("Invalid Password"); }
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

async function suggestForLearning(btn, question, sql, reportName) {
    btn.disabled = true;
    btn.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Checking...`;
    try {
        const response = await fetch('/ai/feedback/suggest', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ question, sql, report_name: reportName })
        });
        const result = await response.json();
        if (result.status === "success" || result.status === "exists") {
            btn.style.background = "#2d3748";
            btn.style.color = result.status === "exists" ? "#63b3ed" : "#48bb78";
            btn.innerHTML = result.status === "exists" ? `<i class="fas fa-info-circle"></i> Already Trained` : `<i class="fas fa-check-circle"></i> Submitted`;
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
            body: JSON.stringify({ question, start_date: startDate, end_date: endDate })
        });
        const result = await response.json();
        
        currentReportData = result.data;
        // CRITICAL: result.report_name must be sent by app.py
        currentReportName = result.report_name || "CustomReport";

        let syncStatusBadge = result.last_sync 
            ? `<div style="font-size: 11px; color: #48bb78; background: #1a202c; padding: 4px 8px; border-radius: 4px; border: 1px solid #2d3748;"><i class="fas fa-history"></i> Last Synced: ${result.last_sync.timestamp}</div>`
            : `<div style="font-size: 11px; color: #718096; background: #1a202c; padding: 4px 8px; border-radius: 4px; border: 1px solid #2d3748;"><i class="fas fa-info-circle"></i> Not yet synced</div>`;

        let tableHtml = `<table style="width:100%; border-collapse: collapse; margin-top:10px; font-size:13px; color: white; background-color: #2c2c2c; border: 1px solid #444;">`;
        if (currentReportData && currentReportData.length > 0 && !currentReportData[0].Error) {
            const headers = Object.keys(currentReportData[0]);
            tableHtml += `<thead><tr style="background-color: #444;">${headers.map(h => `<th style="padding:10px; border:1px solid #555; text-align:left;">${h}</th>`).join('')}</tr></thead><tbody>`;
            tableHtml += currentReportData.map((row, i) => `<tr style="background-color: ${i%2===0?'#333':'#3d3d3d'};">${headers.map(h => `<td style="padding:10px; border:1px solid #555;">${row[h]}</td>`).join('')}</tr>`).join('');
            tableHtml += '</tbody>';
        } else if (currentReportData?.[0]?.Error) {
            tableHtml = `<div style="color:#f56565; padding:10px;">Error: ${currentReportData[0].Error}</div>`;
        }
        tableHtml += '</table>';

        const yearOptions = [2025, 2026, 2027, 2028, 2029, 2030].map(y => `<option value="${y}" ${y===2026?'selected':''}>${y}</option>`).join('');
        const monthOptions = [{v:"01", n:"Jan"}, {v:"02", n:"Feb"}, {v:"03", n:"Mar"}, {v:"04", n:"Apr"}, {v:"05", n:"May"}, {v:"06", n:"Jun"}, {v:"07", n:"Jul"}, {v:"08", n:"Aug"}, {v:"09", n:"Sep"}, {v:"10", n:"Oct"}, {v:"11", n:"Nov"}, {v:"12", n:"Dec"}].map(m => `<option value="${m.v}">${m.n}</option>`).join('');

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
                                style="background:#805ad5; color:white; border:none; padding:8px 14px; border-radius:4px; cursor:pointer; font-size:12px; font-weight:bold;">⭐ Train AI</button>
                    </div>
                    <label style="color:#a0aec0; font-size:12px; cursor:pointer; display: flex; align-items: center; gap: 8px;">
                        <input type="checkbox" onchange="toggleSyncPanel(this)" class="sync-toggle-check" style="cursor:pointer; width:15px; height:15px;"> Sync to DHIS2?
                    </label>
                </div>
                <div class="sync-workflow-container" style="display:none; margin-top:10px;">
                    <div style="background:#2d3748; padding:15px; border-radius:8px; border: 1px solid #4a5568;">
                        <div style="display:flex; gap:10px; margin-bottom:10px;">
                            <div style="flex:1;"><label style="color:#cbd5e0; font-size:10px;">Year</label><select class="sync-year" style="width:100%; padding:8px; border-radius:4px; border:none; background:#1a202c; color:white; font-size:12px;">${yearOptions}</select></div>
                            <div style="flex:1;"><label style="color:#cbd5e0; font-size:10px;">Month</label><select class="sync-month" style="width:100%; padding:8px; border-radius:4px; border:none; background:#1a202c; color:white; font-size:12px;">${monthOptions}</select></div>
                        </div>
                        <input type="text" class="dhis-user" placeholder="DHIS2 Username" style="width:100%; padding:8px; margin-bottom:8px; border-radius:4px; border:none; background:#1a202c; color:white;">
                        <input type="password" class="dhis-pass" placeholder="DHIS2 Password" style="width:100%; padding:8px; margin-bottom:12px; border-radius:4px; border:none; background:#1a202c; color:white;">
                        <button onclick="triggerDHIS2Sync(this)" style="background:#3182ce; color:white; border:none; padding:12px; border-radius:4px; cursor:pointer; font-weight:bold; width:100%;">🚀 Push to DHIS2</button>
                        <div class="sync-status" style="font-size:12px; margin-top:10px; text-align:center;"></div>
                    </div>
                </div>
            </div>`;
        msgArea.innerHTML += aiHtml;
        msgArea.scrollTop = msgArea.scrollHeight;
    } catch (e) { console.error(e); }
}

async function triggerDHIS2Sync(btn) {
    const msgContainer = btn.closest('.ai-msg');
    const statusDiv = msgContainer.querySelector('.sync-status');
    const userIn = msgContainer.querySelector('.dhis-user');
    const passIn = msgContainer.querySelector('.dhis-pass');
    const periodStr = msgContainer.querySelector('.sync-year').value + msgContainer.querySelector('.sync-month').value;
    
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
                data: currentReportData, report_name: currentReportName,
                period: periodStr, dhis_user: userIn.value, dhis_pass: passIn.value
            })
        });
        const res = await response.json();
        if (res.status === "completed") {
            statusDiv.style.color = "#48bb78";
            statusDiv.innerHTML = `✅ ${res.message}`;
            btn.innerText = "Success ✓";
            loadSyncLogs(); 
            btn.style.background = "#2d3748";
        } else {
            statusDiv.style.color = "#f56565";
            statusDiv.innerHTML = `❌ ${res.message}`;
            btn.disabled = false;
            btn.innerText = "🚀 Push to DHIS2";
        }
    } catch (error) {
        statusDiv.innerHTML = `❌ Server Error`;
        btn.disabled = false;
        btn.innerText = "🚀 Push to DHIS2";
    }
}