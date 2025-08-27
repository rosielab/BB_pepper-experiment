


function set_html(id, value) {
    const el = document.getElementById(id);
    if (typeof value === "function") { // some holdovers from jspsych return functions. Others return html
        el.innerHTML = value();
    } else {
        el.innerHTML = value;
    }
}



get_intro = () => {
    var robot_img = `<img id=robot_img src="${ILLUSTRATIONS.robot_img}" class="side-img" style="border: 5px solid blue;">`
    function intro_example(to_append) {
        return `<div class="instructions">
            
            <div class="container">
            ${robot_img}
                <div class="img-container" style="margin-bottom: 10px;  display: flex; justify-content: center; gap: 30px;">
                    <div style="text-align: center;">
                        <p><strong>Target</strong></p>
                        <img src="images/Target/DA_A_9.png" class="img" style="box-shadow: 0 0 10px #000;" border= 5px double blue>
                    </div>
                    <div style="text-align: center;">
                        <p>Non-target</p>
                        <img src="images/Target/DA_B_9.png" class="img" border= 1px solid black>
                    </div>
                </div>
            </div>
            ${to_append}
            </div>
            `;

    };


    return {
        // type: jsPsychInstructions,
        pages:
            [
                `
                <div class="instructions"><br>
                ${robot_img}
                <p><strong>Hello, I'm Pepper! I'm a robot learning to communicate clearly. </strong><br>
                In this study, I will try to improve my speaking skills by describing images. <br>
                Your job is to give me feedback on how I'm doing. </p>
                </div>`,


                `<div class="instructions"><br>
                ${robot_img}
                <p><strong>Here's how it works: </strong><br><br>
                Each time, you'll see two images:
                <div>
                <ol style="display: inline-block; text-align: left; list-style-position: inside; padding-left: 2em; margin: 0 auto;">
                    <li>The <strong>target</strong> image on the left</li>
                    <li>The <strong>non-target</strong> image on the right</li>
                </ol>
                </div><br>
                
                I will try to say a sentence that matches the <strong>target</strong> image.<br> 
                But I might make a mistake in pronunciation, stress, or intonation that changes the meaning of the sentence! <br> 
                If that happens, I might accidentally say a sentence that matches the non-target image instead.</p>                </div>
                `,


                `<div class="instructions"><br>
                ${robot_img}
                <p><strong>Here's your job:</strong><br>
                <p>If you think I spoke correctly:<br> confirm by repeating my sentence.</p>
                <p>But if you think I made a mistake that changes the meaning of my sentence:<br> correct me by repeating my sentence with the correct pronunciation, stress, or intonation.
                </p>
                </ul>
                </p>
                </div>
                `,
                () => {
                    let to_append = `<p>Suppose the trial contains these images.<br>
                    I want to describe the <strong>target image</strong> by saying <strong><i>"she hates to miss, Lee."</i></strong><br>
                    But if my intonation is bad, I might accidentally say <strong><i>"she hates to miss Lee."</i></strong></p>`;
                    return intro_example(to_append);

                },
                () => {
                    let to_append = `<p>If you hear me say <strong>"she hates to miss, Lee"</strong>, confirm that I spoke correctly:<br>
                    Say, "She hates to miss, Lee."<br></p>
                    <p>On the other hand, if you hear me say <strong>"she hates to miss Lee"</strong>, then correct me:<br>
                    Say, "She hates to <i>miss</i>, Lee!"</p>`;
                    return intro_example(to_append);

                },
                () => {
                    let to_append = `<p >
                        When you correct me, try to modify my sentence as little as possible.<br>
                        <div style="text-align: left;">
                        <strong>Examples</strong><br>
                        🤖 I said "She hates to miss Lee", which describes the non-target image on the right.<br>
                        ✅ Correct me by saying: "She hates to miss, Lee!"<br><br>
                        ❌ Don't say: "No, she hates to miss, Lee."<br>
                        ❌ Don't say: "She hates to miss in archery."<br>
                        ❌ Don't say: "The girl and Lee are talking about the archer."<br></div>
                        </p>
                        <p><strong>If you're not sure if I was correct or incorrect, don't worry: just make your best guess.</strong></p>

                        `;
                    return intro_example(to_append);

                },

                `<div class="instructions"><br>
                ${robot_img}
                <p>You'll be able to listen to my sentence as many times as you want.<br>
                When you record your own audio, you'll have one chance to redo.<br>
                If you redo, then your second attempt will be kept.</p>
                <p><strong>Next, let's do some practice trials.</strong></p>
                
                </div>
                `
            ],

    }
}

function get_block_and_trial(curr) {
    let block;
    if (curr.state === 'Practice') return [0, curr.page];
    else block = Math.floor(parseInt(curr.page) / stim_order.length) + 1;
    let trial = parseInt(curr.page) % stim_order.length + 1;
    return [block, trial];
}

function get_study() {
    let pages = [];
    stim_order.forEach(ele => {
        let stim_id = ele[0];
        let version = ele[1];
        // versions are 1: img A,correct; 2: img B,correct; 3: img A,incorrect; 4: img B,incorrect
        // images should be : 1:A, 2:B, 3:A, 4:B
        let img_order = [1, 3].includes(parseInt(version)) ? ["A", "B"] : ["B", "A"];
        let folder = STIM_LOOKUP[stim_id].folder;
        let number = STIM_LOOKUP[stim_id].number;
        let target_img = `${IMAGE_FOLDER}${folder}_${img_order[0]}_${number}.png`;
        let non_target_img = `${IMAGE_FOLDER}${folder}_${img_order[1]}_${number}.png`;
        pages.push(prompt(target_img, non_target_img, ''));

    })
    return pages;

}
function get_practice() {
    let pages = [];
    for (let i = 0; i < PRACTICE_ORDER.length; i++) {
        let ele = PRACTICE_ORDER[i];
        let practice_hints = '';
        if (i === 0) {
            practice_hints = `<div>
                <p style="color: red;">Hint 1: some images have labels to help you figure out the characters' names.<br>
                In the target image, one of the jackets is labelled "Lee".<br> 
                In the non-target image, one of the characters' legs is labelled "Lee".
                </p>
                <p style="color: red;">Hint 2: I actually said <strong>"she hates to miss Lee</strong>"!</p>
                </p>

                </div>`;
        }
        else if (i === 1) {
            practice_hints = `<div>
                <p style="color: red;">Hint: In the target image, the funding is being <strong>pooled</strong><br> 
                In the non-target image, the funding is being <strong>pulled</strong>.
                </p>


                </div>`;
        }
        let stim_id = ele[0];
        let version = ele[1];
        // versions are 1: img A,correct; 2: img B,correct; 3: img A,incorrect; 4: img B,incorrect
        // images should be : 1:A, 2:B, 3:A, 4:B
        let img_order = [1, 3].includes(parseInt(version)) ? ["A", "B"] : ["B", "A"];
        let folder = STIM_LOOKUP[stim_id].folder;
        let number = STIM_LOOKUP[stim_id].number;
        let target_img = `${IMAGE_FOLDER}${folder}_${img_order[0]}_${number}.png`;
        let non_target_img = `${IMAGE_FOLDER}${folder}_${img_order[1]}_${number}.png`;
        pages.push(prompt(target_img, non_target_img, practice_hints));

    }
    return pages;


}
get_fixation = (curr) => {
    if (curr.state === 'Instructions') { // just starting practice
        return `    Starting trial 1 of practice round.<br>
                    <div class="instructions"><br><br>
                    4 trials to go.<br><br>
                    </div>
                    `;
    }
    let [block_num, trial_num] = get_block_and_trial(curr);
    let what_to_start;
    if (block_num == 0) {
        what_to_start = `practice trial ${trial_num + 2}`
    }
    else {
        what_to_start = trial_num != 0 ? `trial ${trial_num + 1}` : `block ${block_num}, trial 1`;
    }
    // practice trial
    if (block_num == 0) {
        var comment = '';
        if (trial_num === 1) {
            comment = '<p style="color: red;">No more hints after this point. Good luck!</p>'
            return `    Starting ${what_to_start} out of 4.<br>
                    <div class="instructions"><br>${comment}<br>
                    </div>
                    `;
        } else if (curr.page == 3) {
            return `    
                    <div class="instructions"><br><br>
                    <strong>You have completed the practice block!</strong><br><br>
                    Now we'll start the study. There will be 4 blocks consisting of ${stim_order.length/4} trials each.<br><br>
                    </div>
                    `;
        } else {
            return `    Starting ${what_to_start}<br>
                    <div class="instructions"><br><br>
                    ${4 - trial_num - 1} practice trial(s) to go.
                    <br><br>
                    </div>
                    `;
        }
    }

    if (block_num != 0 && trial_num == stim_order.length) {
        return `    ${what_to_start}<br>
                    <div class="instructions"><br><br>
                    <strong>Block ${block_num - 1} out of 4 complete!</strong><br><br>
                    </div>
                    `;
    } else {
        return `    Starting block ${block_num }, ${what_to_start}<br>
                    <div class="instructions"><br><br>
                    ${4 - block_num } block(s) to go.<br>
                    ${stim_order.length / 4 - trial_num} trial(s) in this block to go.
                    <br><br>
                    </div>
                    `;
    }

};

prompt = (target_img, non_target_img, to_append) => {

    return `
            <div class="container">
                <div class="img-container" style="margin-bottom: 20px; display: flex; justify-content: center; gap: 30px;">
                    <div style="text-align: center;">
                        <p><strong>Target</strong></p>
                        <img src="${target_img}" class="img" style="box-shadow: 0 0 10px #000;" border= 5px double blue><br>
                    </div>
                    <div style="text-align: center;">
                        <p>Non-target</p>
                        <img src="${non_target_img}" class="img" border= 1px solid black><br>
                    </div>
                </div>
                <div class="container"><p>Did I describe the <strong>target</strong> image correctly?</p></div> 
                ${to_append}
            </div>
        `;
};



function handle_message(command, curr) {
    let before = curr;
    switch (command) {
        case 'n':
            curr = next(curr);
            break;
        case 'b':
            curr = back(curr);
            break;
        case 'f':
            fixation(curr);
            break;
        case 'i':
            curr = goto_instructions(curr);
            break;
        case 'p':
            curr = goto_practice(curr);
            break;
        case 's':
            curr = goto_study(curr);
            break;
    }
    console.log(before, command, curr)
    return curr;
}

function goto_instructions(curr) {
    curr = { state: 'Instructions', page: 0 };
    set_html('content', intro_pages[0]);
    return curr;
}

function goto_practice(curr) {
    curr = { state: 'Practice', page: 0 };
    set_html('content', practice_pages[0]);
    return curr;
}

function fixation(curr) { // Doesn't modify curr.
    if (curr.state === 'Instructions' && curr.page !== intro_pages.length - 1) {
        return;
    }
    else {
        let fixation = get_fixation(curr);
        set_html('content', fixation);
        return;
    }
}

function goto_study(curr) {
    let new_content = STATES['Study'].content;
    curr = { state: 'Study', page: 0 };
    set_html('content', new_content[0]);
    return curr;

}

function next(curr) {
    let statedict = STATES[curr.state]; // 
    let curr_page = curr.page;
    let new_state = curr.state;
    let new_page;
    // finished this stage
    if (curr_page + 1 === statedict.content.length) {
        new_page = 0;
        new_state = statedict.next_state === null ? curr.state : statedict.next_state;

    } else {
        new_page = curr_page + 1;
    }
    let new_content = STATES[new_state].content;
    curr = { state: new_state, page: new_page };
    set_html('content', new_content[new_page]);
    return curr;

}
function back(curr) {
    let statedict = STATES[curr.state]; // 
    let curr_page = curr.page;
    let new_state = curr.state;
    let new_page;
    // finished this stage
    if (curr_page === 0) {
        new_state = statedict.prev_state === null ? curr.state : statedict.prev_state;
        new_page = statedict.prev_state === null ? 0 : STATES[new_state].content.length - 1;
    } else {
        new_page = curr_page - 1;
    }
    let new_content = STATES[new_state].content;
    curr = { state: new_state, page: new_page };
    set_html('content', new_content[new_page]);
    return curr;

}


const ws = new WebSocket(`ws://${location.host}`);

ws.onopen = () => console.log('Connected to server');

ws.onmessage = (event) => {
    try {
        const data = JSON.parse(event.data);
        if (data.type === 'command') {
            curr = handle_message(data.value, curr);
        }
    } catch (err) {
        console.log(err);
    }
};

// Start with intro
const BLOCK_ORDER = 'ABCD';
const intro_pages = get_intro().pages;
const stim_order = get_stimulus_list(BLOCK_ORDER);
const practice_pages = get_practice();
const study_pages = get_study();

const voice_condition = DEFAULT_VOICE_CONDITION;
const STATES = {
    'Instructions': { 'content': intro_pages, 'next_state': 'Practice', 'prev_state': null },
    'Practice': { 'content': practice_pages, 'next_state': 'Study', 'prev_state': 'Instructions' },
    'Study': { 'content': study_pages, 'next_state': null, 'prev_state': 'Practice' }
}
let curr = { state: 'Instructions', page: 0 }
set_html('content', intro_pages[0]);
