document.getElementById('start-btn').onclick = function () {
    const inputLang = document.getElementById('input_language').value;
    const outputLang = document.getElementById('output_language').value;

    fetch('/start_translation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            input_language: inputLang,
            output_language: outputLang
        })
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'started') {
                console.log('Translation started');
            }
        });
};

document.getElementById('stop-btn').onclick = function () {
    fetch('/stop_translation', {
        method: 'POST'
    })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'stopped') {
                console.log('Translation stopped');
            }
        });
};

// Real-time translation stream
const eventSource = new EventSource('/stream');
eventSource.onmessage = function (event) {
    const data = JSON.parse(event.data);
    document.getElementById('translated-text').innerText = data.translation;
};
