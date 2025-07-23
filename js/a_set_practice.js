// --- 상수 설정 ---
const BOX_COLOR_DEFAULT = "#a0aec0";
const BOX_COLOR_FLASH = "#f6e05e";

// --- HTML 요소 가져오기 ---
const canvas = document.getElementById('practice-canvas');
const ctx = canvas.getContext('2d');
const messageLabel = document.getElementById('message-label');
const instructionP = document.getElementById('instruction');
const startMainTestBtn = document.getElementById('start-main-test-btn');

// --- 게임 상태 변수 ---
let problemData = null;
let userSequence = [];
let gameState = 'loading'; // loading, memorizing, answering, processing

/** 박스를 캔버스에 그리는 함수 */
function drawBoxes() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!problemData || !problemData.boxes) return;

    problemData.boxes.forEach(box => {
        ctx.fillStyle = userSequence.includes(box.id) ? BOX_COLOR_FLASH : BOX_COLOR_DEFAULT;
        ctx.fillRect(box.x1, box.y1, box.x2 - box.x1, box.y2 - box.y1);
    });

    userSequence.forEach((boxId, index) => {
        const box = problemData.boxes.find(b => b.id === boxId);
        if (box) {
            ctx.fillStyle = "white";
            ctx.font = "bold 20px Helvetica";
            ctx.textAlign = "center";
            ctx.textBaseline = "middle";
            const centerX = box.x1 + (box.x2 - box.x1) / 2;
            const centerY = box.y1 + (box.y2 - box.y1) / 2;
            ctx.fillText(index + 1, centerX, centerY);
        }
    });
}

/** 문제의 정답 순서대로 박스를 깜빡이는 애니메이션 함수 */
function showFlashingSequence() {
    gameState = 'memorizing';
    messageLabel.textContent = "순서를 기억하세요...";
    instructionP.style.display = 'none';
    
    let delay = 1000;
    problemData.flash_sequence.forEach(boxId => {
        const box = problemData.boxes.find(b => b.id === boxId);
        
        setTimeout(() => {
            if (box) {
                ctx.fillStyle = BOX_COLOR_FLASH;
                ctx.fillRect(box.x1, box.y1, box.x2 - box.x1, box.y2 - box.y1);
            }
        }, delay);

        delay += 500;

        setTimeout(() => {
            if (box) {
                ctx.fillStyle = BOX_COLOR_DEFAULT;
                ctx.fillRect(box.x1, box.y1, box.x2 - box.x1, box.y2 - box.y1);
            }
        }, delay);
        
        delay += 250;
    });

    setTimeout(() => {
        gameState = 'answering';
        messageLabel.textContent = "기억한 순서대로 클릭하세요!";
    }, delay);
}

/** 사용자의 답안을 서버로 전송하는 함수 */
async function submitAnswer() {
    gameState = 'processing';
    messageLabel.textContent = "채점 중입니다...";

    try {
        const response = await fetch('/api/a-set/submit-practice-answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answer: userSequence })
        });
        
        const result = await response.json();

        if (result.status === 'correct') {
            messageLabel.textContent = result.message;
            canvas.style.display = 'none';
            startMainTestBtn.style.display = 'block';
        } else if (result.status === 'incorrect') {
            messageLabel.textContent = result.message;
            setTimeout(retryPractice, 1500);
        } else {
            messageLabel.textContent = `오류: ${result.message || '알 수 없는 오류'}`;
        }
    } catch(error) {
        messageLabel.textContent = '서버 통신에 실패했습니다.';
        console.error('Submit Practice Answer Error:', error);
    }
}

/** 틀렸을 경우, 다시 시도하는 함수 */
function retryPractice() {
    userSequence = [];
    drawBoxes();
    setTimeout(showFlashingSequence, 1000);
}

/** 캔버스 클릭 이벤트 처리 함수 */
function handleCanvasClick(event) {
    if (gameState !== 'answering') return;

    const rect = canvas.getBoundingClientRect();
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    problemData.boxes.forEach(box => {
        if (x >= box.x1 && x <= box.x2 && y >= box.y1 && y <= box.y2) {
            const boxId = box.id;
            
            if (!userSequence.includes(boxId)) {
                 userSequence.push(boxId);
            }
            
            drawBoxes();

            if (userSequence.length === problemData.flash_count) {
                submitAnswer();
            }
        }
    });
}

/** 페이지가 로드될 때, 서버에서 연습 문제를 가져와 테스트 시작 */
async function initializePracticeTest() {
    gameState = 'loading';
    messageLabel.textContent = '연습 문제를 준비 중입니다...';

    try {
        const response = await fetch('/api/a-set/get-practice-problem');
        if (!response.ok) throw new Error('서버에서 문제를 가져오는 데 실패했습니다.');
        
        problemData = await response.json();
        userSequence = [];
        drawBoxes();
        setTimeout(showFlashingSequence, 3000);

    } catch (error) {
        messageLabel.textContent = `오류: ${error.message}`;
        console.error(error);
    }
}

// "본 테스트 시작하기" 버튼 클릭 이벤트
startMainTestBtn.addEventListener('click', () => {
    window.location.href = '/a-set/test';
});

// 캔버스에 클릭 이벤트 리스너 추가
canvas.addEventListener('click', handleCanvasClick);

// 페이지가 처음 로드될 때 테스트 시작
document.addEventListener('DOMContentLoaded', initializePracticeTest);