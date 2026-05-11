// 1. 手輛移動控制：按一次執行 0.3 秒即停止
function move(action) {
    console.log("執行動作: " + action);
    fetch('/move?action=' + action);

    // 如果不是按停止，則在 300 毫秒後自動發送 stop 指令
    if (action !== 'stop') {
        setTimeout(() => {
            console.log("自動停止中...");
            fetch('/move?action=stop');
        }, 300); // 這裡可以根據你想要的「動一下」的距離來調整時間
    }
}

// 2. 舵機角度控制
function controlServo(direction) {
    fetch('/servo?direction=' + direction);
}

// 3. 參數設定 (確保路由正確對應)
function setParam(key, value) {
    fetch(`/set_param?${key}=${value}`)
        .then(response => response.json())
        .then(data => {
            console.log("參數同步:", data);
            // 更新 UI 狀態
            if (key === 'mode') {
                document.getElementById('btn-manual').className = (value === 'manual' ? 'btn active' : 'btn');
                document.getElementById('btn-auto').className = (value === 'auto' ? 'btn active' : 'btn');
            }
        });
}
