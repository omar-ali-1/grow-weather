
  function fetchProfile(userIdToken) {
    console.log(userIdToken);
    $.ajax('/fetchProfile/', {
      /* Set header for the XMLHttpRequest to get data from the web server
      associated with userIdToken */
      headers: {
        'Authorization': 'Bearer ' + userIdToken
      }
    }).then(function(data){
      $('#name').empty();
      // console.log(data);
      // Iterate over user data to display user's notes from database.
      JSON.parse(data).forEach(function(profile){
        $('#name').append($('<p>').text(profile.name));
        $('#bio').append($('<p>').text(profile.bio));
      });
    });
  }

