// static/js/script.js
document.getElementById('uploadForm').addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const form = e.target;
    const fileInput = document.getElementById('excelFile');
    const nPeopleInput = document.getElementById('n_people');
    const statusDiv = document.getElementById('statusMessage');
    const submitBtn = document.getElementById('submitBtn');
    const resultsSection = document.getElementById('resultsSection');

    statusDiv.style.display = 'block';
    statusDiv.className = 'loading';
    statusDiv.textContent = 'กำลังอัพโหลดและรัน Genetic Algorithm... อาจใช้เวลาสักครู่ ⏳';
    submitBtn.disabled = true;
    resultsSection.style.display = 'none';

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('n_people', nPeopleInput.value);

    try {
        const response = await fetch('/calculate', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.status === 'success') {
            statusDiv.className = 'success';
            statusDiv.textContent = `✅ คำนวณเสร็จสิ้น! Variance ที่ดีที่สุดคือ ${data.best_variance}`;
            
            document.getElementById('bestVariance').textContent = data.best_variance;
            
            // แสดงสรุปกลุ่ม
            const groupSummary = document.getElementById('groupSummary');
            groupSummary.innerHTML = data.groups.map(g => 
                `<li>กลุ่ม ${g.Group}: ${g.Total_Workload} หน่วย</li>`
            ).join('');

            // แสดงตารางผลลัพธ์
            const taskTableBody = document.querySelector('#taskTable tbody');
            taskTableBody.innerHTML = data.table_data.map(item => `
                <tr>
                    <td>${item.task}</td>
                    <td>${item.workload}</td>
                    <td>${item.label}</td>
                </tr>
            `).join('');

            // ตั้งค่าปุ่มดาวน์โหลด
            const downloadBtn = document.getElementById('downloadBtn');
            downloadBtn.onclick = () => {
                window.location.href = `/download/${data.download_filename}`;
            };
            
            resultsSection.style.display = 'block';

        } else {
            // แสดงข้อผิดพลาด
            statusDiv.className = 'error';
            statusDiv.textContent = `❌ ข้อผิดพลาด: ${data.error || 'เกิดข้อผิดพลาดที่ไม่ทราบสาเหตุ'}`;
        }

    } catch (error) {
        statusDiv.className = 'error';
        statusDiv.textContent = `❌ เกิดข้อผิดพลาดในการเชื่อมต่อ: ${error.message}`;
        console.error('Fetch error:', error);
    } finally {
        submitBtn.disabled = false;
    }
});