def get_stylesheet():
    return """
    QMainWindow {
        background-color: #2b2b2b;
        font-family: 'Segoe UI', Arial, sans-serif;
    }
    
    QLabel#drop_area {
        background-color: #3d3d3d;
        border: 2px dashed #5a5a5a;
        border-radius: 10px;
        color: #aaaaaa;
        font-size: 18px;
        padding: 20px;
        margin: 10px;
    }
    
    QLabel#drop_area:hover {
        border-color: #7a7a7a;
        background-color: #454545;
    }
    
    QPushButton {
        background-color: #4a4a4a;
        color: #ffffff;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-size: 14px;
        min-width: 80px;
    }
    
    QPushButton:hover {
        background-color: #5a5a5a;
    }
    
    QPushButton:pressed {
        background-color: #3a3a3a;
    }
    
    QPushButton:checked {
        background-color: #4CAF50;
    }
    
    QPushButton:disabled {
        background-color: #3a3a3a;
        color: #aaaaaa;
    }
    
    QProgressBar {
        border: 1px solid #444;
        border-radius: 4px;
        text-align: center;
        height: 20px;
    }
    
    QProgressBar::chunk {
        background-color: #4CAF50;
        border-radius: 2px;
    }
    
    QScrollArea {
        border: none;
        background: #1a1a1a;
        border-radius: 8px;
    }
    
    QLabel#lyricsDisplay {
        font-size: 24px;
        color: white;
        margin: 10px;
        padding: 15px;
        line-height: 1.6;
        background-color: #1a1a1a;
    }
    
    QPushButton[text^="🎤"] {
        min-width: 100px;
        padding: 8px 10px;
    }
    
    QPushButton[text^="🎤"]:checked {
        background-color: #4CAF50;
        border: 1px solid #3a8f3d;
    }
    
    QPushButton[text^="▶"], 
    QPushButton[text^="⏸"], 
    QPushButton[text^="⏹"] {
        font-size: 16px;
    }
    
    /* Estilo para la barra de progreso de la canción */
    #songProgress {
        height: 8px;
        text-align: center;
    }
    
    #songProgress::chunk {
        background-color: #4CAF50;
    }
    """