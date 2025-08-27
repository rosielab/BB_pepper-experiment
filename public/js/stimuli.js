// window.stimulus_count = 30;
// window.practice_count = 3;
const FOLDERS = {
    "human_model": "Stimuli/Audio/Grace/",
    "human_baseline": "Stimuli/Audio/Baseline Human (Olivia)/",
    "humanlike_affective": "Stimuli/Audio/Humanlike_Affective (MatchaTTS)/",
    "humanlike_monotonic": "Stimuli/Audio/Humanlike_Monotonic/",
    "machinelike_affective": "Stimuli/Audio/Machinelike_Affective/",
    "machinelike_monotonic": "Stimuli/Audio/Machinelike_Monotonic/"
}
const IMAGE_FOLDER = "Stimuli/Pictures/";

const ILLUSTRATIONS = {
    robot_img: "Stimuli/Pictures/robot.png",
    rec_icon: "Stimuli/Pictures/mic.png",
    whatdoestheimageshow: "Stimuli/Pictures/whatdoestheimageshow.png",
    gotit: "Stimuli/Pictures/gotit.png",
    wasthatcorrect: "Stimuli/Pictures/wasthatcorrect.png",
    pleasecorrectme: "Stimuli/Pictures/pleasecorrectme.png",
    pleaseconfirm: "Stimuli/Pictures/pleaseconfirm.png",
    correctorconfirm: "Stimuli/Pictures/correctorconfirm.png",
    nap: "Stimuli/Pictures/nap.png",
    app: "Stimuli/Pictures/app.png"
};

const STIM_LIST_PATH = "Stimuli/stimlist.csv";
const STIM_ORDER_PATH = "Stimuli/stimorder.csv"


const PRACTICE_ORDER = [
    ["target_DA_9", '3'],
    ["filler_list_5", '1'],
    ["target_list_2", '2'],
    ["target_DA_4", '4'],
]

// key: stimulus id
// value: [block A version, block B version, block C version, block D version]
// versions: 
// v1: Target image type A; Pepper correct
// v2: Target image type B; Pepper correct
// v3: Target image type A; Pepper incorrect
// v4: Target image type B; Pepper incorrect
// From this dict and the block order (eg DCBA) we get the ordered stimulus list (similar to PRACTICE_ORDER)
const STIM_DICT = {
    "target_DA_1": [1, 2, 3, 4],
    "target_DA_2": [2, 1, 4, 3],
    "target_DA_3": [3, 4, 1, 2],
    "target_DA_5": [4, 3, 2, 1],
    "target_DA_6": [1, 2, 3, 4],
    "target_DA_7": [2, 1, 4, 3],
    "target_DA_8": [3, 4, 1, 2],
    "target_DA_10": [4, 3, 2, 1],
    "target_list_1": [1, 2, 3, 4],
    "target_list_3": [2, 1, 4, 3],
    "target_list_4": [3, 4, 1, 2],
    "target_list_5": [4, 3, 2, 1],
    "target_list_6": [1, 2, 3, 4],
    "target_list_7": [2, 1, 4, 3],
    "target_list_8": [3, 4, 1, 2],
    "target_list_10": [4, 3, 2, 1],
    "filler_DA_1": [1, 2, 3, 4],
    "filler_DA_2": [2, 1, 4, 3],
    "filler_DA_3": [3, 4, 1, 2],
    "filler_DA_4": [4, 3, 2, 1],
    "filler_list_1": [1, 2, 3, 4],
    "filler_list_2": [2, 1, 4, 3],
    "filler_list_3": [3, 4, 1, 2],
    "filler_list_4": [4, 3, 2, 1]
};

const STIM_LOOKUP = {
    "target_DA_1": {
        "folder": "Target/DA",
        "number": 1,
        "A": "She has to pull, Bart.",
        "B": "She has to pull Bart."
    },
    "target_DA_2": {
        "folder": "Target/DA",
        "number": 2,
        "A": "He wants to hit, Gabe.",
        "B": "He wants to hit Gabe."
    },
    "target_DA_3": {
        "folder": "Target/DA",
        "number": 3,
        "A": "They have to trip, Walt.",
        "B": "They have to trip Walt."
    },
    "target_DA_4": {
        "folder": "Target/DA",
        "number": 4,
        "A": "They want to skip, Claire.",
        "B": "They want to skip Claire."
    },
    "target_DA_5": {
        "folder": "Target/DA",
        "number": 5,
        "A": "She likes to see, Reese.",
        "B": "She likes to see Reese."
    },
    "target_DA_6": {
        "folder": "Target/DA",
        "number": 6,
        "A": "I need to kick, Bruce.",
        "B": "I need to kick Bruce."
    },
    "target_DA_7": {
        "folder": "Target/DA",
        "number": 7,
        "A": "She had to lift, Clyde.",
        "B": "She had to lift Clyde."
    },
    "target_DA_8": {
        "folder": "Target/DA",
        "number": 8,
        "A": "She likes to draw, Kim.",
        "B": "She likes to draw Kim."
    },
    "target_DA_9": {
        "folder": "Target/DA",
        "number": 9,
        "A": "She hates to miss, Lee.",
        "B": "She hates to miss Lee."
    },
    "target_DA_10": {
        "folder": "Target/DA",
        "number": 10,
        "A": "He likes to fight, Bill.",
        "B": "He likes to fight Bill."
    },
    "target_list_1": {
        "folder": "Target/List",
        "number": 1,
        "A": "The man got a child, a ball, and a game.",
        "B": "The man got a child a ball and a game."
    },
    "target_list_2": {
        "folder": "Target/List",
        "number": 2,
        "A": "I emailed his mates, a chef, and a thief.",
        "B": "I emailed his mates a chef and a thief."
    },
    "target_list_3": {
        "folder": "Target/List",
        "number": 3,
        "A": "The child baked my friends, a cake, and a loaf.",
        "B": "The child baked my friends a cake and a loaf."
    },
    "target_list_4": {
        "folder": "Target/List",
        "number": 4,
        "A": "The lad gave the girl, a shirt, and a blouse.",
        "B": "The lad gave the girl a shirt and a blouse."
    },
    "target_list_5": {
        "folder": "Target/List",
        "number": 5,
        "A": "The man showed his wife, his spy, and his guard.",
        "B": "The man showed his wife his spy and his guard."
    },
    "target_list_6": {
        "folder": "Target/List",
        "number": 6,
        "A": "The girl saw her pals, Elise, and Marie.",
        "B": "The girl saw her pals Elise and Marie."
    },
    "target_list_7": {
        "folder": "Target/List",
        "number": 7,
        "A": "We went to our cats, Yvonne, and Tyrone.",
        "B": "We went to our cats Yvonne and Tyrone."
    },
    "target_list_8": {
        "folder": "Target/List",
        "number": 8,
        "A": "She followed her maids, Nicole, and Simone.",
        "B": "She followed her maids Nicole and Simone."
    },
    "target_list_9": {
        "folder": "Target/List",
        "number": 9,
        "A": "The mom drove her kids, Eugene, and Adele.",
        "B": "The mom drove her kids Eugene and Adele."
    },
    "target_list_10": {
        "folder": "Target/List",
        "number": 10,
        "A": "She painted her guests, Yvonne, and Louise.",
        "B": "She painted her guests Yvonne and Louise."
    },
    "filler_DA_1": {
        "folder": "Filler/Filler_DA",
        "number": 1,
        "A": "I felt the heat, man.",
        "B": "I felt the hit, man."
    },
    "filler_DA_2": {
        "folder": "Filler/Filler_DA",
        "number": 2,
        "A": "Just take the lead, Kate.",
        "B": "Just take the lid, Kate."
    },
    "filler_DA_3": {
        "folder": "Filler/Filler_DA",
        "number": 3,
        "A": "They found a knot, Jill.",
        "B": "They found a nut, Jill."
    },
    "filler_DA_4": {
        "folder": "Filler/Filler_DA",
        "number": 4,
        "A": "You made the cot, Nate.",
        "B": "You made the cut, Nate."
    },
    "filler_DA_5": {
        "folder": "Filler/Filler_DA",
        "number": 5,
        "A": "The baby cooed, Zack.",
        "B": "The baby could, Zach."
    },
    "filler_list_1": {
        "folder": "Filler/Filler_List",
        "number": 1,
        "A": "The box had a game, a doll, and a sheep.",
        "B": "The box had a game, a doll, and a ship."
    },
    "filler_list_2": {
        "folder": "Filler/Filler_List",
        "number": 2,
        "A": "The yard had a bush, a tree, and a bean.",
        "B": "The yard had a bush, a tree, and a bin."
    },
    "filler_list_3": {
        "folder": "Filler/Filler_List",
        "number": 3,
        "A": "The girl saw a beach, a boat, and a dock.",
        "B": "The girl saw a beach, a boat, and a duck."
    },
    "filler_list_4": {
        "folder": "Filler/Filler_List",
        "number": 4,
        "A": "The boy drew a room, a chair, and a cop.",
        "B": "The boy drew a room, a chair, and a cup."
    },
    "filler_list_5": {
        "folder": "Filler/Filler_List",
        "number": 5,
        "A": "The funding was planned, assessed, and then pooled.",
        "B": "The funding was planned, assessed, and then pulled."
    },
    "demo_3": {
        "folder": "Demo/Demo",
        "number": 3,
        "A": "Don't, let me pay!",
        "B": "Don't let me pay!"
    },
    "demo_2": {
        "folder": "Demo/Demo",
        "number": 2,
        "A": "I'm sorry, I love you.",
        "B": "I'm sorry I love you."
    }
}
function shuffle(array) {
    var currentIndex = array.length, temporaryValue, randomIndex;
    // While there remain elements to shuffle...
    while (0 !== currentIndex) {
        // Pick a remaining element...
        randomIndex = Math.floor(Math.random() * currentIndex);
        currentIndex -= 1;
        // And swap it with the current element.
        temporaryValue = array[currentIndex];
        array[currentIndex] = array[randomIndex];
        array[randomIndex] = temporaryValue;
    }

    return array;
}

/**
 * Returns an ordered list of dicts.
 * @param {string} voice_condition
 * @param {dict} stim_dict - Keys are sentence_ids. Values are tuples [1, 2, 3, 4] corresponding to the stimulus version for blocks A, B, C, D
 * @param {string} block_order -'ABCD' for example
 * @returns {Array<Object>} Ordered list of tuples [stimulus_id, version]. 
 */
function get_stimulus_list(block_order) {
    let stim_list = [];
    for (let i = 0; i < block_order.length; i++) {
        let block_list = []
        Object.entries(STIM_DICT).forEach(([stim_id, values]) => {
            block_list.push([stim_id, values[i]])
        });
        block_list = shuffle(block_list);
        stim_list = stim_list.concat(block_list);
    }
    return stim_list;

}