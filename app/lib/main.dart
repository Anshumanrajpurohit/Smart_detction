import 'dart:async';
import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'package:path/path.dart';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

List<CameraDescription> cameras = [];

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  cameras = await availableCameras();
  runApp(CameraApp());
}

class CameraApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: CameraHome(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class CameraHome extends StatefulWidget {
  @override
  _CameraHomeState createState() => _CameraHomeState();
}

class _CameraHomeState extends State<CameraHome> {
  CameraController? controller;
  bool isCameraActive = true;
  Timer? _timer;
  Uuid uuid = Uuid();

  // 🔑 Supabase Config (replace with your actual values)
  final String supabaseUrl = "https://hwxyuvtfoyzycggbypmo.supabase.co";
  final String supabaseKey =
      "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imh3eHl1dnRmb3l6eWNnZ2J5cG1vIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1Mjk5Njk1NiwiZXhwIjoyMDY4NTcyOTU2fQ.wNZitOMcjXGAAMbmOLuS-eRpaKPzsaPM0vZ2FKXpAho";
  final String bucketName = "android";

  @override
  void initState() {
    super.initState();
    _initializeCamera();
  }

  Future<void> _initializeCamera() async {
    if (cameras.isEmpty) {
      print("No cameras available.");
      return;
    }

    controller = CameraController(cameras[0], ResolutionPreset.high);

    try {
      await controller!.initialize();
      if (!mounted) return;
      setState(() {});
      _timer =
          Timer.periodic(Duration(seconds: 20), (_) => _captureAndUpload());
    } catch (e) {
      print("Camera init error: $e");
    }
  }

  Future<void> _captureAndUpload() async {
    if (controller == null || !controller!.value.isInitialized) return;

    try {
      final image = await controller!.takePicture();

      final dir = await getTemporaryDirectory();
      final String filename = "${uuid.v4()}.jpg";
      final File imageFile = File(join(dir.path, filename));
      await image.saveTo(imageFile.path);

      final bytes = await imageFile.readAsBytes();

      final uploadUrl = '$supabaseUrl/storage/v1/object/$bucketName/$filename';

      final response = await http.post(
        Uri.parse(uploadUrl),
        headers: {
          'Authorization': 'Bearer $supabaseKey',
          'Content-Type': 'application/octet-stream',
          'x-upsert': 'true',
        },
        body: bytes,
      );

      if (response.statusCode == 200 || response.statusCode == 201) {
        print("✅ Uploaded $filename");
      } else {
        print("❌ Upload failed: ${response.statusCode} - ${response.body}");
      }
    } catch (e) {
      print("❗ Error capturing or uploading: $e");
    }
  }

  void stopCamera() {
    controller?.dispose();
    _timer?.cancel();
    setState(() {
      controller = null;
      isCameraActive = false;
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    controller?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("Live Camera Auto Upload")),
      body: Column(
        children: [
          Expanded(
            child: isCameraActive &&
                    controller != null &&
                    controller!.value.isInitialized
                ? CameraPreview(controller!)
                : Center(child: Text("Camera Stopped")),
          ),
          ElevatedButton(
            onPressed: stopCamera,
            child: Text("Stop"),
          ),
        ],
      ),
    );
  }
}
