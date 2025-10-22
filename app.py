import pandas as pd
import numpy as np
import os
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import io

app = Flask(__name__)
# กำหนดโฟลเดอร์สำหรับอัพโหลด
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# =================================================================
# ส่วนของ Genetic Algorithm (GA) Logic
# =================================================================

class GeneticDivider:
    def __init__(self, workloads, N, pool_size=1000, generations=500):
        self.workloads = np.array(workloads)
        self.num_tasks = len(workloads)
        self.N = N  # จำนวนกลุ่ม
        self.pool_size = pool_size
        self.generations = generations
        
    def _create_initial_pool(self):
        """สุ่มสร้าง Chromosome ชุดเริ่มต้น"""
        # แต่ละ chromosome คือ array ความยาว num_tasks มีค่า 1 ถึง N
        return np.random.randint(1, self.N + 1, size=(self.pool_size, self.num_tasks))

    def _fitness_function(self, chromosome):
        """คำนวณ Variance ของ Workload แต่ละกลุ่ม (ยิ่งน้อยยิ่งดี)"""
        group_sums = np.zeros(self.N)
        for i in range(self.N):
            # i+1 คือ label
            group_sums[i] = self.workloads[chromosome == (i + 1)].sum()
        
        # Fitness คือ Variance (ค่าความแปรปรวน)
        return np.var(group_sums)

    def _selection(self, pool, fitnesses, top_k=50):
        """คัดเลือก Chromosome ที่ดีที่สุด K อันดับแรก"""
        sorted_indices = np.argsort(fitnesses)
        return pool[sorted_indices[:top_k]]

    def _crossover(self, parent1, parent2):
        """Crossover (การผสมข้าม): Single-point crossover"""
        point = np.random.randint(1, self.num_tasks)
        child = np.concatenate((parent1[:point], parent2[point:]))
        return child

    def _change_mutation(self, chromosome, rate=0.1):
        """Change Mutation: สุ่มเปลี่ยน label ของบางตำแหน่ง"""
        mutated_chromosome = chromosome.copy()
        for i in range(self.num_tasks):
            if np.random.rand() < rate:
                # สุ่มเปลี่ยนเป็น label ใหม่ (1 ถึง N)
                mutated_chromosome[i] = np.random.randint(1, self.N + 1)
        return mutated_chromosome

    def _swap_mutation(self, chromosome, rate=0.1):
        """Swap Mutation: สลับ label ของสองตำแหน่งแบบสุ่ม"""
        mutated_chromosome = chromosome.copy()
        if np.random.rand() < rate:
            idx1, idx2 = np.random.choice(self.num_tasks, 2, replace=False)
            mutated_chromosome[idx1], mutated_chromosome[idx2] = mutated_chromosome[idx2], mutated_chromosome[idx1]
        return mutated_chromosome
    
    def run(self):
        """รัน Genetic Algorithm"""
        current_pool = self._create_initial_pool()
        
        for generation in range(self.generations):
            # 1. Calculate Fitness
            fitnesses = np.array([self._fitness_function(c) for c in current_pool])
            
            # 2. Selection
            # คัดเลือก 50 ตัวที่ดีที่สุด
            elite_pool = self._selection(current_pool, fitnesses)
            
            new_pool = elite_pool.tolist()
            
            # 3. Reproduction (Crossover + Mutation)
            while len(new_pool) < self.pool_size:
                # สุ่มเลือกพ่อแม่ 2 ตัวจาก elite_pool
                p1_idx, p2_idx = np.random.choice(len(elite_pool), 2, replace=False)
                parent1 = elite_pool[p1_idx]
                parent2 = elite_pool[p2_idx]
                
                # Crossover
                child = self._crossover(parent1, parent2)
                
                # Mutation (ใช้ Change และ Swap)
                child = self._change_mutation(child, rate=0.05)
                child = self._swap_mutation(child, rate=0.05)
                
                new_pool.append(child)

            current_pool = np.array(new_pool)

            # ตรวจสอบและแสดงผลลัพธ์ที่ดีที่สุดในรอบนั้นๆ (Optional)
            if generation % 50 == 0 or generation == self.generations - 1:
                best_fitness = self._fitness_function(elite_pool[0])
                print(f"Gen {generation}: Best Variance = {best_fitness:.2f}")

        # หา Chromosome ที่ดีที่สุดใน generation สุดท้าย
        final_fitnesses = np.array([self._fitness_function(c) for c in current_pool])
        best_index = np.argmin(final_fitnesses)
        best_chromosome = current_pool[best_index]
        best_variance = final_fitnesses[best_index]

        return best_chromosome, best_variance

# =================================================================
# ส่วนของ Flask Routes
# =================================================================

@app.route('/')
def index():
    """หน้าหลักของ Web App"""
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    """จัดการการอัพโหลดไฟล์และการคำนวณ GA"""
    if 'file' not in request.files or 'n_people' not in request.form:
        return jsonify({"error": "Missing file or number of people (N)."}), 400

    file = request.files['file']
    n_people_str = request.form.get('n_people', '2')
    
    try:
        N = int(n_people_str)
        if N < 2:
            return jsonify({"error": "Number of people (N) must be at least 2."}), 400
    except ValueError:
        return jsonify({"error": "Invalid value for N."}), 400

    if file.filename == '':
        return jsonify({"error": "No selected file."}), 400

    if file:
        filename = secure_filename(file.filename)
        # อ่านไฟล์ Excel โดยตรงจาก memory
        try:
            df = pd.read_excel(file.stream)
        except Exception as e:
            return jsonify({"error": f"Error reading Excel file: {e}"}), 400

        # ตรวจสอบและเตรียมข้อมูล
        if 'task' not in df.columns.str.lower() or 'workload' not in df.columns.str.lower():
            return jsonify({"error": "Excel columns must contain 'Task' and 'Workload'."}), 400
        
        # ปรับชื่อคอลัมน์ให้เป็นพิมพ์เล็กทั้งหมดเพื่อความสะดวก
        df.columns = df.columns.str.lower()
        
        tasks = df['task'].tolist()
        workloads = df['workload'].astype(float).tolist()
        
        if len(workloads) < N:
            return jsonify({"error": f"Number of tasks ({len(workloads)}) must be greater than or equal to N ({N})."}), 400

        # รัน Genetic Algorithm
        divider = GeneticDivider(workloads, N)
        best_labels, best_variance = divider.run()

        # สร้าง DataFrame ผลลัพธ์
        result_df = df.copy()
        result_df['label'] = best_labels
        
        # คำนวณผลรวม Workload ของแต่ละกลุ่มเพื่อแสดงผล
        group_results = []
        for i in range(1, N + 1):
            group_workload = result_df[result_df['label'] == i]['workload'].sum()
            group_results.append({
                "Group": i, 
                "Total_Workload": round(group_workload, 2)
            })

        # บันทึก DataFrame ลงใน memory buffer เพื่อส่งให้ดาวน์โหลด
        excel_buffer = io.BytesIO()
        result_df.to_excel(excel_buffer, index=False)
        excel_buffer.seek(0)
        
        # สร้างชื่อไฟล์สำหรับดาวน์โหลด
        download_filename = f"Task_Division_N{N}_Result.xlsx"
        
        # บันทึกไฟล์ลงในโฟลเดอร์ชั่วคราว (เพื่อรอการดาวน์โหลด)
        temp_file_path = os.path.join(app.config['UPLOAD_FOLDER'], download_filename)
        with open(temp_file_path, 'wb') as f:
             f.write(excel_buffer.getbuffer())
        
        # ส่งผลลัพธ์การคำนวณและรายละเอียดสำหรับการแสดงผลบนหน้าเว็บ
        return jsonify({
            "status": "success",
            "best_variance": round(best_variance, 2),
            "groups": group_results,
            "table_data": result_df.to_dict('records'),
            "download_filename": download_filename
        })

@app.route('/download/<filename>', methods=['GET'])
def download_file(filename):
    """ส่งไฟล์ผลลัพธ์ให้ดาวน์โหลด"""
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    return jsonify({"error": "File not found."}), 404

if __name__ == '__main__':
    # สำหรับ deploy บน Render.com ให้ตั้งค่า PORT ผ่าน Environment Variable
    port = int(os.environ.get("PORT", 5000)) 
    app.run(host='0.0.0.0', port=port, debug=True)