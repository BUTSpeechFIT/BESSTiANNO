segment2color = {};
const participant_id = (window.location.pathname.split("/"))[2]
console.log("AA");
(function (Peaks) {

    var renderSegments = function (peaks) {
        var segmentsContainer = document.getElementById('segments');
        var segments = peaks.segments.getSegments();
        var html = '';

        segments.sort(dynamicSort("startTime"));
        for (var i = 0; i < segments.length; i++) {
            var segment = segments[i];

            var row = '<tr>' +
                '<td style="background-color: ' + segment.color + '">' + segment.labelText + '</td>' +
                '<td>' + segment.startTime.toFixed(2) + '</td>' +
                '<td>' + segment.endTime.toFixed(2) + '</td>' +
                '<td>' + '<a href="#' + segment.id + '" data-action="play-segment" data-id="' + segment.id + '">Play</a>' + '</td>' +
                '<td>' + '<a href="#' + segment.id + '" data-action="remove-segment" data-id="' + segment.id + '">X</a>' + '</td>' +
                '</tr>';
            html += row;
        }

        segmentsContainer.querySelector('tbody').innerHTML = html;

        if (html.length) {
            segmentsContainer.classList.remove('hide');
        }
    }

    function dynamicSort(property) {
        var sortOrder = 1;
        if (property[0] === "-") {
            sortOrder = -1;
            property = property.substr(1);
        }
        return function (a, b) {
            /* next line works with strings and numbers,
             * and you may want to customize it to your needs
             */
            var result = (a[property] < b[property]) ? -1 : (a[property] > b[property]) ? 1 : 0;
            return result * sortOrder;
        }
    }

    var AudioContext = window.AudioContext || window.webkitAudioContext;
    var audioContext = new AudioContext();
    var audioElement = document.getElementById('audio');
    var options = {
        containers: {
            zoomview: document.getElementById('zoomview-container'),
            overview: document.getElementById('overview-container')
        },
        mediaElement: audioElement,
        webAudio: {
            audioContext: audioContext,
            scale: 128,
            multiChannel: false
        },
        emitCueEvents: true,
        keyboard: true,
        pointMarkerColor: '#006eb0',
        showPlayheadTime: true,
        zoomLevels: [16000, 32000, 64000],
        randomizeSegmentColor: true,
        scale: 16000,
        segmentStartMarkerColor: "black",
    };

    console.log("CC");

    peak = Peaks.init(options, function (err, peaksInstance) {
        window.peakVars = {
            peaksInstance: peaksInstance,
            renderSegments: renderSegments,
        };
        $("body").removeClass("loading");
        if (err) {
            console.error(err.message);
            return;
        }

        console.log('Peaks instance ready');
        $(".loader").addClass("hide");
        $.getJSON("/segments/" + participant_id, function (data) {
            $.each(data['segments'], function (key, val) {
                window.peakVars.peaksInstance.segments.add({
                    startTime: val[1],
                    endTime: val[2],
                    labelText: val[0],
                    editable: true,
                    color: segment2color[val[0]]
                });

                window.peakVars.renderSegments(window.peakVars.peaksInstance);
            });
            $("#comment")[0].value = data['comment'];
            $("#complete")[0].checked = data['complete'];
            $("#segments-controls").removeClass("hide");
        });

        console.log("Preparing to attach")
        document.querySelector('button[data-action="download"]').addEventListener('click', function (event) {
            // TODO: Download all the segmentation and point results.
            console.log("Downloading");
            segments = peaksInstance.segments.getSegments();
            let toSave = {};
            segments.forEach((obj) => {
                toSave[obj._id] = {
                    startTime: obj._startTime,
                    endTime: obj._endTime,
                    id: obj._id,
                    labelText: obj._labelText
                };
            });

            // Save points
            points = peaksInstance.points.getPoints();
            let toSavePoints = {};
            points.forEach((obj) => {
                toSavePoints[obj._id] = {
                    startTime: obj._time,
                    id: obj._id,
                    labelText: obj._labelText
                };
            });
            let payload = {};
            payload["segments"] = toSave;
            payload["complete"] = $("#complete")[0].checked;
            payload["comment"] = $("#comment")[0].value
            console.log(payload);
            $.post(
                "/segments/" + participant_id,
                JSON.stringify(payload),
                function (data) {
                    console.log("Response: " + data);
                    $("#result").text(data);
                    setTimeout(() => {
                        $("#result").text("");
                        console.log("Hiding");
                    }, 2000);
                }
            );
        });

        document.querySelector('body').addEventListener('click', function (event) {
            var element = event.target;
            var action = element.getAttribute('data-action');
            var id = element.getAttribute('data-id');

            if (action === 'play-segment') {
                var segment = peaksInstance.segments.getSegment(id);
                peaksInstance.player.playSegment(segment);
                vid.currentTime = peaksInstance.player.getCurrentTime();
                vid.play()
            } else if (action === 'remove-segment') {
                peaksInstance.segments.removeById(id);
                renderSegments(peaksInstance);
            }
        });

        // Segment mouse events

        peaksInstance.on('segments.dragend', function (segment) {
            console.log('segments.dragend:', segment);
            peaksInstance.player.seek(segment.endTime)
            renderSegments(peaksInstance);
        });

        peaksInstance.on('segments.dragmove', function (point) {
            console.log('segments.dragmove:', point);
            peaksInstance.player.seek(point.time)
        });

        // DO STUFF ON VIDEOS
        var vid = document.getElementById("video");
        vid.defaultMuted = true;

        peaksInstance.on('player_play', function (segment) {
            vid.currentTime = peaksInstance.player.getCurrentTime();
            vid.play()
        });
        peaksInstance.on('player_pause', function (segment) {
            vid.currentTime = peaksInstance.player.getCurrentTime();
            vid.pause()
        });
        peaksInstance.on('player_seek', function (segment) {
            vid.currentTime = peaksInstance.player.getCurrentTime();
        });

        vid.onplay = function () {
            peaksInstance.player.seek(vid.currentTime);
            peaksInstance.player.play()
        };

        vid.onpause = function () {
            peaksInstance.player.seek(vid.currentTime);
            peaksInstance.player.pause()
        };
    });
})(peaks);


// Submit button
function submitSegmentButtonStatic(buttonValue, color) {
    let btn = document.createElement("button");
    btn.innerHTML = buttonValue;
    btn.id = buttonValue;
    btn.style = "background-color:" + color
    btn.classList.add('button-30');
    $(btn).attr("data-action", "add-segment");
    segment2color[buttonValue] = color;
    btn.addEventListener('click', function () {
        startTime = window.peakVars.peaksInstance.player.getCurrentTime()
        window.peakVars.peaksInstance.segments.add({
            startTime: startTime,
            endTime: startTime + 3,
            labelText: this.innerHTML,
            editable: true,
            color: color,
        });
        window.peakVars.renderSegments(window.peakVars.peaksInstance);
    });
    document.getElementById("point-buttons").appendChild(btn);
}

const colors = {
    olive: '#3d9970',
    blue: '#0074d9',
    lime: '#01ff70',
    teal: '#39cccc',
    aqua: '#7fdbff',
    red: '#ff4136',
    green: '#2ecc40',
    orange: '#ff851b',
    purple: '#b10dc9',
    yellow: '#ffdc00',
    fuchsia: '#f012be',
    gray: '#aaaaaa',
    white: '#ffffff',
    black: '#111111',
    silver: '#dddddd'
};

$.getJSON("/segmentation/allowed", function (data) {
    let colorArray = Object.values(colors);
    $.each(data, function (key, val) {
        submitSegmentButtonStatic(val, colorArray[key]);
    });
});

const fileUrl = "/video/" + participant_id;
$(".video").attr("src", fileUrl);
$(".audio").attr("src", fileUrl);
var video = document.getElementById('video');
document.onkeypress = function (e) {
    if ((e || window.event).keyCode === 32) {
        video.paused ? video.play() : video.pause();
    }
};