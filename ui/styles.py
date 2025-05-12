def get_stylesheet():
    return """
    QMainWindow {
        background-color: #2b2b2b;
    }
    
    QLabel {
        color: #ffffff;
        font-size: 16px;
    }
    
    QLabel#drop_area {
        background-color: #3d3d3d;
        border: 2px dashed #5a5a5a;
        border-radius: 10px;
        color: #aaaaaa;
        font-size: 18px;
        padding: 20px;
    }
    
    QLabel#drop_area:hover {
        border-color: #7a7a7a;
    }
    
    QPushButton {
        background-color: #4a4a4a;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-size: 14px;
    }
    
    QPushButton:hover {
        background-color: #5a5a5a;
    }
    
    QPushButton:disabled {
        background-color: #3a3a3a;
        color: #7a7a7a;
    }
    
    QProgressBar {
        border: 1px solid #444;
        border-radius: 4px;
        text-align: center;
    }
    
    QProgressBar::chunk {
        background-color: #4CAF50;
        width: 10px;
    }
    
    QLabel#lyrics_display {
        font-size: 24px;
        color: #ffffff;
        margin: 20px;
        background-color: rgba(0, 0, 0, 0.3);
        border-radius: 10px;
        padding: 20px;
    }
    """