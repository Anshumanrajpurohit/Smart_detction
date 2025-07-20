import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:typed_data';
import 'package:image_picker/image_picker.dart';
import 'dart:io';


dependencies:
flutter:
  sdk: flutter
http: ^0.13.5
image_picker: ^0.8.6
permission_handler: ^10.2.0


void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Face Recognition & Age/Gender API',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        visualDensity: VisualDensity.adaptivePlatformDensity,
      ),
      home: FaceRecognitionApp(),
    );
  }
}

class FaceRecognitionApp extends StatefulWidget {
  @override
  _FaceRecognitionAppState createState() => _FaceRecognitionAppState();
}

class _FaceRecognitionAppState extends State<FaceRecognitionApp> {
  // Replace with your ngrok URL
  final String baseUrl = 'https://your-ngrok-url.ngrok.io';
  
  // State variables
  String _result = '';
  String _systemStatus = 'Unknown';
  bool _isLoading = false;
  bool _backgroundRunning = false;
  Map<String, dynamic>? _databaseStats;
  List<dynamic>? _peopleList;
  File? _selectedImage;
  
  final ImagePicker _picker = ImagePicker();

  @override
  void initState() {
    super.initState();
    _getSystemStatus();
  }

  // Convert image to base64
  Future<String> _imageToBase64(File image) async {
    List<int> imageBytes = await image.readAsBytes();
    return base64Encode(imageBytes);
  }

  // Get system status
  Future<void> _getSystemStatus() async {
    setState(() => _isLoading = true);
    
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/status'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _systemStatus = data['status'] ?? 'Unknown';
          _backgroundRunning = data['background_tasks'] ?? false;
          _databaseStats = data['database_stats'];
        });
      } else {
        setState(() => _systemStatus = 'Error: ${response.statusCode}');
      }
    } catch (e) {
      setState(() => _systemStatus = 'Connection Error: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // Get people list from database
  Future<void> _getPeopleList() async {
    setState(() => _isLoading = true);
    
    try {
      final response = await http.get(
        Uri.parse('$baseUrl/people'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _peopleList = data['people'];
          _result = 'Found ${data['total']} people in database';
        });
      } else {
        setState(() => _result = 'Error getting people: ${response.statusCode}');
      }
    } catch (e) {
      setState(() => _result = 'Connection Error: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // Predict age and gender from image
  Future<void> _predictAgeGender() async {
    if (_selectedImage == null) {
      setState(() => _result = 'Please select an image first');
      return;
    }

    setState(() => _isLoading = true);
    
    try {
      String base64Image = await _imageToBase64(_selectedImage!);
      
      final response = await http.post(
        Uri.parse('$baseUrl/predict-age-gender'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'image_base64': base64Image,
          'include_age': true,
          'include_gender': true,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success']) {
          setState(() {
            _result = 'Prediction Results:\n'
                'Age: ${data['age'] ?? 'N/A'}\n'
                'Gender: ${data['gender'] ?? 'N/A'}\n'
                'Confidence: ${data['confidence'] ?? 'N/A'}\n'
                'Processing Time: ${data['processing_time']?.toStringAsFixed(2) ?? 'N/A'}s';
          });
        } else {
          setState(() => _result = 'Prediction Error: ${data['error']}');
        }
      } else {
        setState(() => _result = 'API Error: ${response.statusCode}');
      }
    } catch (e) {
      setState(() => _result = 'Connection Error: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // Start face recognition cycle
  Future<void> _startFaceRecognition() async {
    setState(() => _isLoading = true);
    
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/face-recognition'),
        headers: {'Content-Type': 'application/json'},
        body: json.encode({
          'detection_time': 20,
          'camera_index': 0,
        }),
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        if (data['success']) {
          setState(() {
            _result = 'Face Recognition Results:\n'
                'Faces Detected: ${data['faces_detected']}\n'
                'Total People: ${data['total_people']}\n'
                'New Faces: ${data['new_faces']}\n'
                'Message: ${data['message']}';
            _peopleList = data['people_list'];
          });
        } else {
          setState(() => _result = 'Recognition Error: ${data['message']}');
        }
      } else {
        setState(() => _result = 'API Error: ${response.statusCode}');
      }
    } catch (e) {
      setState(() => _result = 'Connection Error: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // Start background recognition
  Future<void> _startBackgroundRecognition() async {
    setState(() => _isLoading = true);
    
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/start-background-recognition'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _result = data['message'];
          _backgroundRunning = true;
        });
      } else {
        setState(() => _result = 'Error starting background: ${response.statusCode}');
      }
    } catch (e) {
      setState(() => _result = 'Connection Error: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // Stop background recognition
  Future<void> _stopBackgroundRecognition() async {
    setState(() => _isLoading = true);
    
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/stop-background-recognition'),
        headers: {'Content-Type': 'application/json'},
      );

      if (response.statusCode == 200) {
        final data = json.decode(response.body);
        setState(() {
          _result = data['message'];
          _backgroundRunning = false;
        });
      } else {
        setState(() => _result = 'Error stopping background: ${response.statusCode}');
      }
    } catch (e) {
      setState(() => _result = 'Connection Error: $e');
    } finally {
      setState(() => _isLoading = false);
    }
  }

  // Pick image from gallery
  Future<void> _pickImage() async {
    final XFile? image = await _picker.pickImage(source: ImageSource.gallery);
    if (image != null) {
      setState(() {
        _selectedImage = File(image.path);
      });
    }
  }

  // Take photo with camera
  Future<void> _takePhoto() async {
    final XFile? image = await _picker.pickImage(source: ImageSource.camera);
    if (image != null) {
      setState(() {
        _selectedImage = File(image.path);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('Face Recognition & ML API'),
        actions: [
          IconButton(
            icon: Icon(Icons.refresh),
            onPressed: _getSystemStatus,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // System Status Card
            Card(
              child: Padding(
                padding: EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'System Status',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 8),
                    Text('Status: $_systemStatus'),
                    Text('Background Tasks: ${_backgroundRunning ? "Running" : "Stopped"}'),
                    if (_databaseStats != null) ...[
                      Text('Total People: ${_databaseStats!['total_people']}'),
                      Text('Total Visits: ${_databaseStats!['total_visits']}'),
                    ],
                  ],
                ),
              ),
            ),

            SizedBox(height: 16),

            // Image Selection Section
            Card(
              child: Padding(
                padding: EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Image Selection',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton.icon(
                            icon: Icon(Icons.photo_library),
                            label: Text('Pick from Gallery'),
                            onPressed: _pickImage,
                          ),
                        ),
                        SizedBox(width: 8),
                        Expanded(
                          child: ElevatedButton.icon(
                            icon: Icon(Icons.camera_alt),
                            label: Text('Take Photo'),
                            onPressed: _takePhoto,
                          ),
                        ),
                      ],
                    ),
                    if (_selectedImage != null) ...[
                      SizedBox(height: 8),
                      Container(
                        height: 200,
                        decoration: BoxDecoration(
                          border: Border.all(color: Colors.grey),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(8),
                          child: Image.file(
                            _selectedImage!,
                            fit: BoxFit.cover,
                            width: double.infinity,
                          ),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),

            SizedBox(height: 16),

            // Action Buttons
            Card(
              child: Padding(
                padding: EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Actions',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 8),
                    
                    // Age/Gender Prediction
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        icon: Icon(Icons.face),
                        label: Text('Predict Age & Gender'),
                        onPressed: _isLoading ? null : _predictAgeGender,
                      ),
                    ),
                    
                    SizedBox(height: 8),
                    
                    // Face Recognition
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        icon: Icon(Icons.search),
                        label: Text('Run Face Recognition'),
                        onPressed: _isLoading ? null : _startFaceRecognition,
                      ),
                    ),
                    
                    SizedBox(height: 8),
                    
                    // Background Tasks
                    Row(
                      children: [
                        Expanded(
                          child: ElevatedButton.icon(
                            icon: Icon(Icons.play_arrow),
                            label: Text('Start Background'),
                            onPressed: _isLoading || _backgroundRunning ? null : _startBackgroundRecognition,
                            style: ElevatedButton.styleFrom(backgroundColor: Colors.green),
                          ),
                        ),
                        SizedBox(width: 8),
                        Expanded(
                          child: ElevatedButton.icon(
                            icon: Icon(Icons.stop),
                            label: Text('Stop Background'),
                            onPressed: _isLoading || !_backgroundRunning ? null : _stopBackgroundRecognition,
                            style: ElevatedButton.styleFrom(backgroundColor: Colors.red),
                          ),
                        ),
                      ],
                    ),
                    
                    SizedBox(height: 8),
                    
                    // Get People List
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton.icon(
                        icon: Icon(Icons.people),
                        label: Text('Get People List'),
                        onPressed: _isLoading ? null : _getPeopleList,
                      ),
                    ),
                  ],
                ),
              ),
            ),

            SizedBox(height: 16),

            // Results Display
            Card(
              child: Padding(
                padding: EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Results',
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    SizedBox(height: 8),
                    Container(
                      width: double.infinity,
                      padding: EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: Colors.grey[100],
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: _isLoading 
                        ? Center(child: CircularProgressIndicator())
                        : Text(
                            _result.isEmpty ? 'No results yet' : _result,
                            style: TextStyle(fontSize: 14),
                          ),
                    ),
                  ],
                ),
              ),
            ),

            SizedBox(height: 16),

            // People List Display
            if (_peopleList != null && _peopleList!.isNotEmpty) ...[
              Card(
                child: Padding(
                  padding: EdgeInsets.all(16.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'People in Database (${_peopleList!.length})',
                        style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                      ),
                      SizedBox(height: 8),
                      ListView.builder(
                        shrinkWrap: true,
                        physics: NeverScrollableScrollPhysics(),
                        itemCount: _peopleList!.length,
                        itemBuilder: (context, index) {
                          final person = _peopleList![index];
                          return Card(
                            margin: EdgeInsets.only(bottom: 8),
                            child: ListTile(
                              leading: CircleAvatar(
                                child: Text('${index + 1}'),
                              ),
                              title: Text(person['name'] ?? 'Unknown'),
                              subtitle: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text('Visits: ${person['visits']}'),
                                  Text('Quality: ${person['quality']?.toStringAsFixed(2) ?? 'N/A'}'),
                                  Text('Last seen: ${person['last_seen'] ?? 'Unknown'}'),
                                ],
                              ),
                              isThreeLine: true,
                            ),
                          );
                        },
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}