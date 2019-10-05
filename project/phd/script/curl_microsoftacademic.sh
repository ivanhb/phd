@ECHO OFF

curl --header "Ocp-Apim-Subscription-Key: 6df9932fc55549179681d2c9739ae306" -v -X GET "https://api.labs.cognitive.microsoft.com/academic/v1.0/calchistogram?expr=Ti='Emotion detection for wheelchair navigation enhancement'&model=latest&attributes=F.FN&count=10&offset=0" --data-ascii "{body}"
