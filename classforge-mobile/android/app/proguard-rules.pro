# Flutter ProGuard Rules for Classforge Visualizer

# Flutter wrapper & plugins
-keep class io.flutter.app.** { *; }
-keep class io.flutter.plugin.** { *; }
-keep class io.flutter.util.** { *; }
-keep class io.flutter.view.** { *; }
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }

# Google Play Core deferred components
-dontwarn com.google.android.play.core.**

# Core desugaring & reflection
-dontwarn java.lang.invoke.**
-dontwarn javax.annotation.**
-keepattributes *Annotation*
-keepattributes Signature
-keepattributes InnerClasses
-keepattributes EnclosingMethod

# Keep data models
-keepclassmembers class * {
    @com.google.gson.annotations.SerializedName <fields>;
}
