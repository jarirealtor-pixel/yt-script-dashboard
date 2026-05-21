// ===== 데이터 관리 (LocalStorage 기반) =====

const DB = {
    // 데이터 가져오기
    get(key) {
        try {
            const data = localStorage.getItem('broker_' + key);
            return data ? JSON.parse(data) : [];
        } catch {
            return [];
        }
    },

    // 데이터 저장
    set(key, data) {
        localStorage.setItem('broker_' + key, JSON.stringify(data));
    },

    // 항목 추가
    add(key, item) {
        const list = this.get(key);
        item.id = Date.now().toString();
        item.createdAt = new Date().toISOString();
        list.push(item);
        this.set(key, list);
        return item;
    },

    // 항목 수정
    update(key, id, updates) {
        const list = this.get(key);
        const idx = list.findIndex(item => item.id === id);
        if (idx !== -1) {
            list[idx] = { ...list[idx], ...updates };
            this.set(key, list);
            return list[idx];
        }
        return null;
    },

    // 항목 삭제
    remove(key, id) {
        const list = this.get(key).filter(item => item.id !== id);
        this.set(key, list);
    },

    // ID로 찾기
    findById(key, id) {
        return this.get(key).find(item => item.id === id);
    }
};

// 고객 유형 매핑
const CUSTOMER_TYPES = {
    buyer: '매수인',
    seller: '매도인',
    tenant: '세입자',
    agent: '참여중개사'
};

// 매물 유형 매핑
const PROPERTY_TYPES = {
    apt: '아파트',
    villa: '빌라/다세대',
    officetel: '오피스텔',
    house: '단독/다가구',
    store: '상가',
    office: '사무실',
    land: '토지'
};

// 거래 유형 매핑
const DEAL_TYPES = {
    sale: '매매',
    jeonse: '전세',
    monthly: '월세'
};

// 일정 유형 매핑
const SCHEDULE_TYPES = {
    viewing: '집보기',
    contract: '계약',
    meeting: '미팅'
};

// 일정 상태 매핑
const SCHEDULE_STATUS = {
    confirmed: '확정',
    pending: '대기',
    cancelled: '취소',
    completed: '완료'
};

// 날짜 포맷 유틸
function formatDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    const month = d.getMonth() + 1;
    const day = d.getDate();
    const weekdays = ['일', '월', '화', '수', '목', '금', '토'];
    const weekday = weekdays[d.getDay()];
    return `${month}/${day}(${weekday})`;
}

function formatTime(timeStr) {
    if (!timeStr) return '';
    const [h, m] = timeStr.split(':');
    const hour = parseInt(h);
    const ampm = hour < 12 ? '오전' : '오후';
    const h12 = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
    return `${ampm} ${h12}:${m}`;
}

function formatDateTime(dateStr, timeStr) {
    return `${formatDate(dateStr)} ${formatTime(timeStr)}`;
}

function formatPhone(phone) {
    if (!phone) return '';
    const cleaned = phone.replace(/\D/g, '');
    if (cleaned.length === 11) {
        return `${cleaned.slice(0,3)}-${cleaned.slice(3,7)}-${cleaned.slice(7)}`;
    }
    if (cleaned.length === 10) {
        return `${cleaned.slice(0,3)}-${cleaned.slice(3,6)}-${cleaned.slice(6)}`;
    }
    return phone;
}

function formatPrice(price) {
    if (!price) return '';
    const num = parseInt(price);
    if (num >= 10000) {
        const uk = Math.floor(num / 10000);
        const man = num % 10000;
        return man > 0 ? `${uk}억 ${man.toLocaleString()}만원` : `${uk}억`;
    }
    return `${num.toLocaleString()}만원`;
}

function isToday(dateStr) {
    const today = new Date().toISOString().split('T')[0];
    return dateStr === today;
}

function getTodayStr() {
    return new Date().toISOString().split('T')[0];
}

// 토스트 메시지
function showToast(message) {
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2500);
}
