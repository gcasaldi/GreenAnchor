#!/usr/bin/env python3
import re

# Read the file
with open('index.html', 'r') as f:
    content = f.read()

# Fix 1: Replace the "Scopri di più" button to have onclick handler
old_button = '''                    <button class="btn btn-secondary">
                        <i class="fas fa-book"></i> Scopri di più
                    </button>'''

new_button = '''                    <button class="btn btn-secondary" onclick="document.getElementById('aboutSection').scrollIntoView({behavior: 'smooth'})">
                        <i class="fas fa-book"></i> Scopri di più
                    </button>'''

content = content.replace(old_button, new_button, 1)  # Replace only first occurrence

# Fix 2: Add About Section before footer
about_section = '''
            <section class="about-section" id="aboutSection">
                <div class="section-title">
                    <i class="fas fa-user-circle"></i>
                    <span>Chi Siamo</span>
                </div>
                <div class="about-content">
                    <div class="about-text">
                        <h3>GreenAnchor - Consolidamento Campagne Ambientali</h3>
                        <p>
                            GreenAnchor è un hub indipendente che non crea né gestisce campagne ambientali, ma organizza 
                            dati pubblici da fonti verificate e rimanda sempre alla sorgente originale per partecipare. 
                            La nostra missione: <strong>consolidare, non frammentare</strong>. Non creiamo un'altra campagna, 
                            portiamone una a termine.
                        </p>
                        <p style="margin-top: 1rem;">
                            <strong>Perché solo 16 campagne?</strong> Stiamo ancora ottimizzando la ricerca su Change.org 
                            e l'API della Commissione UE. Lavoriamo per aggiungere più fonti (Avaaz, WWF, Greenpeace, Legambiente) 
                            e migliorare la raccolta dati. Ogni campagna è verificata al 100% prima di essere pubblicata.
                        </p>
                    </div>
                    <div class="about-author">
                        <h3>Creato da Giulia Casaldi</h3>
                        <div class="author-bio">
                            <p><strong>AI Engineer & Cybersecurity Specialist</strong></p>
                            <p>Splunk Specialist | NIS2 DORA Compliance Expert</p>
                            <p style="color: var(--text-muted); font-size: 0.9rem; margin-top: 0.5rem;">
                                Passionata di tecnologia sostenibile e soluzioni intelligenti per l'ambiente.
                            </p>
                        </div>
                        <div class="author-buttons">
                            <button class="btn-author" onclick="visitAuthor('github')">
                                <i class="fab fa-github"></i> GitHub
                            </button>
                            <button class="btn-author" onclick="visitAuthor('website')">
                                <i class="fas fa-globe"></i> Sito Web
                            </button>
                            <button class="btn-author" onclick="visitAuthor('linkedin')">
                                <i class="fab fa-linkedin"></i> LinkedIn
                            </button>
                        </div>
                        <div id="authorResponse" style="margin-top: 1.5rem; padding: 1rem; background: rgba(0, 217, 111, 0.1); border-radius: 10px; border: 1px solid var(--border-color); display: none; color: var(--primary); font-size: 0.9rem; text-align: center;">
                        </div>
                    </div>
                </div>
            </section>
'''

# Insert before closing footer tag
footer_start = content.find('<footer>')
if footer_start != -1:
    content = content[:footer_start] + about_section + '\n        ' + content[footer_start:]

# Fix 3: Add CSS for about section before media queries
css_section = '''
        /* About Section */
        .about-section {
            margin: 4rem 0;
            padding: 3rem;
            background: rgba(15, 30, 56, 0.5);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border-color);
            border-radius: 20px;
            animation: slideUp 0.8s ease-out;
        }

        .about-content {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 3rem;
            margin-top: 2rem;
        }

        .about-text h3 {
            font-size: 1.5rem;
            margin-bottom: 1rem;
            color: var(--primary);
        }

        .about-text p {
            line-height: 1.8;
            color: var(--text-light);
            margin-bottom: 1rem;
        }

        .about-author {
            background: rgba(0, 217, 111, 0.08);
            border: 1px solid var(--border-color);
            border-radius: 15px;
            padding: 2rem;
            text-align: center;
        }

        .about-author h3 {
            font-size: 1.3rem;
            margin-bottom: 0.5rem;
            background: linear-gradient(135deg, var(--primary), var(--primary-light));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .author-bio {
            margin: 1.5rem 0;
        }

        .author-bio p {
            margin: 0.5rem 0;
            color: var(--text-light);
        }

        .author-bio p:first-child {
            font-weight: 600;
            color: var(--primary);
        }

        .author-buttons {
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
            margin-top: 1.5rem;
        }

        .btn-author {
            padding: 0.7rem 1.5rem;
            background: rgba(0, 217, 111, 0.1);
            border: 1px solid var(--border-color);
            color: var(--primary);
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-weight: 600;
            font-size: 0.9rem;
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
        }

        .btn-author:hover {
            border-color: var(--primary);
            background: rgba(0, 217, 111, 0.2);
            transform: translateY(-3px);
            box-shadow: 0 5px 20px rgba(0, 217, 111, 0.2);
        }

'''

# Find where to insert CSS (before @media)
media_query_index = content.find('@media (max-width: 768px)')
if media_query_index != -1:
    # Find the comment line before @media
    comment_index = content.rfind('/* Responsive */', 0, media_query_index)
    if comment_index != -1:
        content = content[:comment_index] + css_section + '        /* Responsive */\n        ' + content[comment_index + len('/* Responsive */\n        '):]

# Fix 4: Add JavaScript function before closing script
js_function = '''
        function visitAuthor(link) {
            const responseDiv = document.getElementById('authorResponse');
            const messages = {
                github: {
                    text: '✨ Visita il profilo GitHub di Giulia - Codice open source e progetti innovativi',
                    url: 'https://github.com/gcasaldi'
                },
                website: {
                    text: '🌐 Scopri tutti i progetti e competenze di Giulia - Best AI Engineer & Cybersecurity Expert',
                    url: 'https://gcasaldi.github.io/giuliacasaldi.github.io/'
                },
                linkedin: {
                    text: '💼 Connettiti con Giulia su LinkedIn - Splunk Specialist & NIS2 DORA Expert',
                    url: 'https://www.linkedin.com/in/giuliacasaldi'
                }
            };

            if (messages[link]) {
                responseDiv.textContent = messages[link].text;
                responseDiv.style.display = 'block';
                responseDiv.style.animation = 'none';
                setTimeout(() => {
                    responseDiv.style.animation = 'slideUp 0.5s ease-out';
                }, 10);
                setTimeout(() => {
                    window.open(messages[link].url, '_blank');
                }, 800);
            }
        }

'''

# Insert before window.addEventListener
script_end_index = content.find('window.addEventListener(\'load\', loadCampaigns);')
if script_end_index != -1:
    content = content[:script_end_index] + js_function + '        ' + content[script_end_index:]

# Add mobile responsive CSS for about section
mobile_css = '''
            .about-content {
                grid-template-columns: 1fr;
                gap: 1.5rem;
            }

            .about-section {
                padding: 1.5rem;
            }

'''

# Find the closing of @media query and add there
media_close = content.rfind('}', content.find('@media (max-width: 768px)'))
if media_close != -1:
    # Check if it's the right closing brace
    test_section = content[media_close:media_close+50]
    if '}' in test_section:
        # Insert before the final }
        content = content[:media_close] + '\n\n            ' + mobile_css.strip() + '\n        ' + content[media_close:]

# Write the fixed file
with open('index.html', 'w') as f:
    f.write(content)

print("✅ File fixed successfully!")
