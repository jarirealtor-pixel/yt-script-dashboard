// ===== 앱 메인 로직 =====

// 페이지 네비게이션
function navigateTo(pageName, btn) {
    // 페이지 전환
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + pageName).classList.add('active');

    // 네비 활성화
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    if (btn) btn.classList.add('active');

    // 헤더 업데이트
    const titles = {
        dashboard: '대시보드',
        customers: '고객 관리',
        properties: '매물 관리',
        schedules: '일정 관리',
        documents: '자료 / 계약서'
    };
    document.getElementById('headerSubtitle').textContent = titles[pageName] || '';

    // 각 페이지 데이터 로드
    switch (pageName) {
        case 'dashboard':
            updateDashboard();
            break;
        case 'customers':
            renderCustomers();
            break;
        case 'properties':
            renderProperties();
            break;
        case 'schedules':
            renderSchedules();
            break;
        case 'documents':
            document.getElementById('documentContent').innerHTML = '';
            break;
    }
}

// 모달 열기/닫기
function openModal(html) {
    const overlay = document.getElementById('modalOverlay');
    const content = document.getElementById('modalContent');
    content.innerHTML = html;
    overlay.classList.add('active');
    document.body.style.overflow = 'hidden';
}

function closeModal() {
    const overlay = document.getElementById('modalOverlay');
    overlay.classList.remove('active');
    document.body.style.overflow = '';
}

// 대시보드 업데이트
function updateDashboard() {
    const customers = DB.get('customers');
    const properties = DB.get('properties');
    const schedules = DB.get('schedules');
    const contracts = DB.get('contracts');
    const today = getTodayStr();

    const todayScheds = schedules.filter(s =>
        s.date === today && s.status !== 'cancelled'
    );
    const activeContracts = contracts.length;

    // 숫자 업데이트
    document.getElementById('totalCustomers').textContent = customers.length;
    document.getElementById('totalProperties').textContent = properties.length;
    document.getElementById('todaySchedules').textContent = todayScheds.length;
    document.getElementById('totalContracts').textContent = activeContracts;

    // 오늘 일정 렌더링
    const schedContainer = document.getElementById('todayScheduleList');
    if (todayScheds.length === 0) {
        schedContainer.innerHTML = '<div class="empty-state">오늘 예정된 일정이 없습니다</div>';
    } else {
        schedContainer.innerHTML = todayScheds.map(s => {
            const customer = s.customerId ? DB.findById('customers', s.customerId) : null;
            return `
                <div class="list-item" onclick="navigateTo('schedules', document.querySelectorAll('.nav-item')[3]);showScheduleDetail('${s.id}')">
                    <div class="list-item-header">
                        <span class="list-item-name">${formatTime(s.time)}</span>
                        <span class="badge badge-${s.type}">${SCHEDULE_TYPES[s.type]}</span>
                    </div>
                    <div class="list-item-sub">${s.title}</div>
                    ${customer ? `<div class="list-item-sub">고객: ${customer.name}</div>` : ''}
                </div>
            `;
        }).join('');
    }

    // 최근 고객 렌더링 (최근 5명)
    const custContainer = document.getElementById('recentCustomerList');
    const recentCusts = customers.slice(-5).reverse();
    if (recentCusts.length === 0) {
        custContainer.innerHTML = '<div class="empty-state">등록된 고객이 없습니다</div>';
    } else {
        custContainer.innerHTML = recentCusts.map(c => `
            <div class="list-item" onclick="navigateTo('customers', document.querySelectorAll('.nav-item')[1]);showCustomerDetail('${c.id}')">
                <div class="list-item-header">
                    <span class="list-item-name">${c.name}</span>
                    <span class="badge badge-${c.type}">${CUSTOMER_TYPES[c.type]}</span>
                </div>
                <div class="list-item-sub">${formatPhone(c.phone)}</div>
            </div>
        `).join('');
    }
}

// 초기화
document.addEventListener('DOMContentLoaded', () => {
    updateDashboard();
});
