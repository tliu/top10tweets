window.onload = attachListeners;




function attachListeners() {
    $("#go-button").click(function() {
        $("#go-button").attr("disabled", true);
        $("#num-minutes").attr("disabled", true);
        $("#num-tweets").attr("disabled", true);
        $("#tweet-container").empty();
        for (var i = 0; i < $("#num-tweets").val(); i++) {
            var source = $("#tweet-template").html();
            var template = Handlebars.compile(source);
            var context = {id: i}
            var html = template(context);
            console.log(html);
            $("#tweet-container").append(html);
        }

        $.ajax("http://localhost:5000/start/" + $("#num-minutes").val())
        .done(function() {
            console.log("Told the server to start polling.");
        })
        .fail(function() {
            alert("Bad news, something went wrong");
        });

        getTopTweets();

    })
}

function getTopTweets() {
    $.ajax("http://127.0.0.1:5000/top/" + $("#num-tweets").val())
    .done(function(msg) {
        console.log(msg);
        for (var i = 0; i < msg.tweets.length; i++) {
            $("#tweet-" + i).find("#tweet-author").html(msg.tweets[i].author);
            $("#tweet-" + i).find("#tweet-count").html("retweeted " + msg.tweets[i].count + " times in the last " + $("#num-minutes").val() + " minutes.");
            $("#tweet-" + i).find("#tweet-text").html(msg.tweets[i].text);
        }
    })
    .fail(function() {
        alert("Bummer dude, something broke.");
    })
    setTimeout(getTopTweets, 500);
}
