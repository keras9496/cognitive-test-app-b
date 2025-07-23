// --- 상수 설정 ---
const BOX_COLOR_DEFAULT = "#a0aec0";
const BOX_COLOR_FLASH = "#f6e05e";

// --- HTML 요소 가져오기 ---
const canvas = document.getElementById('test-canvas');
const ctx = canvas.getContext('2d');
const messageLabel = document.getElementById('message-label');

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
    messageLabel.textContent = "결과를 확인 중입니다...";

    try {
        await fetch('/api/a-set/submit-answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ answer: userSequence })
        });
        await initializeTest();
    } catch(error) {
        messageLabel.textContent = '서버 통신에 실패했습니다.';
        console.error('Submit Answer Error:', error);
    }
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
            const boxIndex = userSequence.indexOf(boxId);
            if (boxIndex > -1) {
                userSequence.splice(boxIndex, 1);
            } else {
                userSequence.push(boxId);
            }
            drawBoxes();
            if (userSequence.length === problemData.flash_count) {
                submitAnswer();
            }
        }
    });
}

/** 페이지가 로드되거나 다음 문제로 넘어갈 때, 서버에서 문제를 가져와 테스트 시작 */
async function initializeTest() {
    userSequence = [];
    gameState = 'loading';
    messageLabel.textContent = '문제를 가져오는 중입니다...';

    try {
        const response = await fetch('/api/a-set/get-problem');
        if (!response.ok) throw new Error('서버에서 문제를 가져오는 데 실패했습니다.');

        problemData = await response.json();

        if(problemData.status === 'completed') {
            messageLabel.textContent = problemData.message;
            setTimeout(() => {
                window.location.href = problemData.next_url;
            }, 2000);
            return;
        }

        messageLabel.innerHTML = `${problemData.level_name} (${problemData.problem_in_level}/${problemData.total_problems})<br>잠시 후 시작됩니다.`;
        drawBoxes();
        setTimeout(showFlashingSequence, 1500);

    } catch (error) {
        messageLabel.textContent = `오류: ${error.message}`;
        console.error(error);
    }
}

canvas.addEventListener('click', handleCanvasClick);
document.addEventListener('DOMContentLoaded', initializeTest);