# google_mlkit_text_recognition declares optional language recognizers as
# compileOnly dependencies. R8 must not fail when those optional artifacts are
# not packaged by the app.
-dontwarn com.google.mlkit.vision.text.chinese.**
-dontwarn com.google.mlkit.vision.text.devanagari.**
-dontwarn com.google.mlkit.vision.text.japanese.**
-dontwarn com.google.mlkit.vision.text.korean.**
